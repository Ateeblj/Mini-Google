#include <bits/stdc++.h>
#include <fstream>
#include <sstream>
#include <dirent.h>
#include <sys/stat.h>
#include "json.hpp"

// ====================== CUSTOM QUEUE STRUCT (FIXED SIZE, GENERIC & NO STL) ======================

#define MAX_QUEUE_SIZE 1024

template <typename T>
struct FixedQueue {
    T arr[MAX_QUEUE_SIZE];
    int front, rear, count;

    void init() { front = 0; rear = 0; count = 0; }
    bool empty() const { return count == 0; }
    bool full() const { return count == MAX_QUEUE_SIZE; }
    void clear() { front = rear = count = 0; }

    bool push(const T& x) {
        if (full()) return false;
        arr[rear] = x;
        rear = (rear + 1) % MAX_QUEUE_SIZE;
        count++;
        return true;
    }
    bool pop() {
        if (empty()) return false;
        front = (front + 1) % MAX_QUEUE_SIZE;
        count--;
        return true;
    }
    // Front element; must not be called if empty
    T& front_elem() { return arr[front]; }
    // For const context
    const T& front_elem() const { return arr[front]; }
};

// ------------------ Generic Singly Linked List Implementation (No STL) -------------------------

template<typename T>
struct LinkedListNode {
    T val;
    LinkedListNode* next;
    LinkedListNode(const T &v) : val(v), next(nullptr) {}
};

template<typename T>
struct LinkedList {
    LinkedListNode<T>* head;
    LinkedListNode<T>* tail;
    int size;
    LinkedList() : head(nullptr), tail(nullptr), size(0) {}
    ~LinkedList() { clear(); }

    void push_back(const T& val) {
        auto* n = new LinkedListNode<T>(val);
        if (!tail) head = tail = n;
        else {
            tail->next = n;
            tail = n;
        }
        ++size;
    }
    void clear() {
        auto* node = head;
        while (node) {
            auto* next = node->next;
            delete node;
            node = next;
        }
        head = tail = nullptr;
        size = 0;
    }
    // For iteration: for (auto* n = list.head; n; n = n->next) ...
    // Deep copy (used in a few cases)
    LinkedList(const LinkedList& other) : head(nullptr), tail(nullptr), size(0) {
        for (auto* n = other.head; n; n = n->next) this->push_back(n->val);
    }
    LinkedList& operator=(const LinkedList& other) {
        if (this == &other) return *this;
        clear();
        for (auto* n = other.head; n; n = n->next) this->push_back(n->val);
        return *this;
    }
};

// For small fixed-length positions in Posting
#define MAX_POSTING_POSITIONS 50

#ifdef _WIN32
    #include <windows.h>
#endif

using json = nlohmann::json;
using namespace std;

// ====================== ULTRA-FAST TRIE (no sequence STL used) ======================
class UltraFastTrie {
    struct Node {
        Node* children[26] = {nullptr};
        bool is_end = false;
        ~Node() {
            for (int i = 0; i < 26; i++) if (children[i]) delete children[i];
        }
    };
    Node* root;
    // Manual string key->result linked list cache:
    struct PrefixCacheEntry {
        string key;
        LinkedList<string> results;
        PrefixCacheEntry* next;
    };
    mutable PrefixCacheEntry* prefix_cache_head;
    mutable int prefix_cache_size = 0;
    mutable int max_cache_size = 1000;

    // ** Helper: Find cache entry for key **
    const LinkedList<string>* find_in_cache(const string& key) const {
        for (auto* entry = prefix_cache_head; entry; entry = entry->next) {
            if (entry->key == key) return &entry->results;
        }
        return nullptr;
    }
    // ** Helper: Insert into cache **
    void insert_in_cache(const string& key, LinkedList<string>& results) const {
        if (prefix_cache_size >= max_cache_size) {
            // Remove first entry
            auto* to_del = prefix_cache_head;
            prefix_cache_head = prefix_cache_head->next;
            delete to_del;
            prefix_cache_size--;
        }
        // Copy list
        auto* entry = new PrefixCacheEntry{key, results, prefix_cache_head};
        prefix_cache_head = entry;
        prefix_cache_size++;
    }
    void clear_cache() {
        auto* n = prefix_cache_head;
        while (n) {
            auto* nxt = n->next;
            delete n;
            n = nxt;
        }
        prefix_cache_head = nullptr;
        prefix_cache_size = 0;
    }
public:
    UltraFastTrie() : root(new Node()), prefix_cache_head(nullptr) {}
    ~UltraFastTrie() { delete root; clear_cache(); }
    void insert(const string& word) {
        if (word.empty() || word.length() > 25) return;
        Node* cur = root;
        for (char c : word) {
            int idx = c - 'a';
            if (idx < 0 || idx >= 26) return;
            if (!cur->children[idx]) cur->children[idx] = new Node();
            cur = cur->children[idx];
        }
        cur->is_end = true;
    }
    LinkedList<string> starts_with(const string& prefix, int limit = 10) const {
        string cache_key = prefix + "|" + to_string(limit);
        if (auto found = find_in_cache(cache_key)) return *found;
        LinkedList<string> results;
        if (prefix.empty()) {
            insert_in_cache(cache_key, results);
            return results;
        }
        Node* cur = root;
        for (char c : prefix) {
            int idx = c - 'a';
            if (idx < 0 || idx >= 26 || !cur->children[idx]) {
                insert_in_cache(cache_key, results);
                return results;
            }
            cur = cur->children[idx];
        }
        // BFS using custom queue, store up to limit
        typedef pair<Node*, string> Qtype;
        FixedQueue<Qtype> q;
        q.init();
        q.push(Qtype(cur, prefix));
        while (!q.empty() && results.size < limit) {
            Node* node = q.front_elem().first;
            string str = q.front_elem().second;
            q.pop();
            if (node->is_end) results.push_back(str);
            for (int i = 0; i < 26 && results.size < limit; i++) {
                if (node->children[i]) q.push(Qtype(node->children[i], str + char('a' + i)));
            }
        }
        insert_in_cache(cache_key, results);
        return results;
    }
    void clear() {
        delete root;
        root = new Node();
        clear_cache();
    }
};

// ====================== ULTRA-FAST UTILITIES ======================
static inline string toLowerFast(const string &s) {
    string out;
    out.reserve(s.size());
    for (char c : s) out.push_back((char)tolower((unsigned char)c));
    return out;
}

// Custom LinkedList<string> replacement for vector<string> return
LinkedList<string> tokenize_ultrafast(const string &text) {
    LinkedList<string> tokens;
    if (text.empty()) return tokens;
    const char* ptr = text.c_str();
    char buffer[32];
    int buf_idx = 0;
    static const unordered_set<string> STOP_WORDS = {
        "the", "and", "for", "are", "but", "not", "you", "all", "any", "can",
        "had", "her", "was", "one", "our", "out", "day", "get", "has", "him",
        "his", "how", "man", "new", "now", "old", "see", "two", "way", "who",
        "boy", "did", "its", "let", "put", "say", "she", "too", "use", "may",
        "also", "than", "that", "this", "with", "from", "have", "were", "been",
        "they", "what", "when", "where", "which", "will", "your", "their"
    };
    int n_added = 0;
    while (*ptr && n_added < 100000) {
        unsigned char c = *ptr;
        if (isalnum(c)) {
            if (buf_idx < 31) buffer[buf_idx++] = tolower(c);
        } else if (buf_idx > 0) {
            buffer[buf_idx] = '\0';
            if (buf_idx >= 2 && buf_idx <= 15) {
                string word(buffer, buf_idx);
                if (STOP_WORDS.find(word) == STOP_WORDS.end() &&
                    !all_of(word.begin(), word.end(), ::isdigit)) {
                    tokens.push_back(move(word)); n_added++;
                }
            }
            buf_idx = 0;
        }
        ptr++;
    }
    if (buf_idx > 0 && buf_idx >= 2 && buf_idx <= 15) {
        buffer[buf_idx] = '\0';
        string word(buffer, buf_idx);
        if (STOP_WORDS.find(word) == STOP_WORDS.end() &&
            !all_of(word.begin(), word.end(), ::isdigit))
            tokens.push_back(move(word));
    }
    return tokens;
}
string read_full_file_content(const string& content) { return content; }

// Use LinkedList for query_terms, but internally vector for local pairs (vector used only in the smallest scope for sort)
string get_snippet_improved(const string& text, const LinkedList<string>& query_terms) {
    if (text.empty() || !query_terms.head) return "";
    vector<pair<size_t, string>> matches;
    for (auto* node = query_terms.head; node; node = node->next) {
        const string& term = node->val;
        if (term.length() < 2) continue;
        size_t pos = 0;
        while ((pos = text.find(term, pos)) != string::npos) {
            matches.emplace_back(pos, term);
            pos += 1;
        }
    }
    if (matches.empty()) {
        for (size_t i = 0; i < text.length(); i++) {
            if (isalpha(text[i])) {
                size_t start = i;
                size_t end = text.find('\n', start);
                if (end == string::npos) end = text.length();
                string snippet = text.substr(start, min((size_t)300, end - start));
                if (snippet.length() > 50) return snippet;
            }
        }
        return text.substr(0, min((size_t)300, text.length()));
    }
    sort(matches.begin(), matches.end());
    for (auto& match : matches) {
        size_t pos = match.first;
        size_t context_start = (pos > 200) ? pos - 200 : 0;
        size_t context_end = min(pos + 200, text.length());
        string snippet = text.substr(context_start, context_end - context_start);
        if (context_start > 0) snippet = "..." + snippet;
        if (context_end < text.length()) snippet += "...";
        if (snippet.length() > 100) return snippet;
    }
    return text.substr(0, min((size_t)300, text.length()));
}

// ====================== OPTIMIZED DIRECTORY SCANNER (No sequence STL) ======================
LinkedList<string> scan_files_optimized(const string& dirpath) {
    LinkedList<string> files;
#ifdef _WIN32
    string search_path = dirpath + "/*.txt";
    WIN32_FIND_DATAA find_data;
    HANDLE hFind = FindFirstFileA(search_path.c_str(), &find_data);
    if (hFind != INVALID_HANDLE_VALUE) {
        do {
            if (!(find_data.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) {
                string filename = find_data.cFileName;
                string full_path = dirpath + "/" + filename;
                struct stat file_stat;
                if (stat(full_path.c_str(), &file_stat) == 0) {
                    if (file_stat.st_size <= 200 * 1024 * 1024) {
                        files.push_back(full_path);
                    }
                }
            }
        } while (FindNextFileA(hFind, &find_data) != 0);
        FindClose(hFind);
    }
#else
    DIR* dir = opendir(dirpath.c_str());
    if (dir) {
        struct dirent* entry;
        while ((entry = readdir(dir)) != nullptr) {
            string filename = entry->d_name;
            if (filename.length() > 4 && filename.substr(filename.length() - 4) == ".txt") {
                string full_path = dirpath + "/" + filename;
                struct stat file_stat;
                if (stat(full_path.c_str(), &file_stat) == 0 && S_ISREG(file_stat.st_mode)) {
                    if (file_stat.st_size <= 200 * 1024 * 1024) {
                        files.push_back(full_path);
                    }
                }
            }
        }
        closedir(dir);
    }
#endif
    // Sort manually
    struct SorterNode {
        string fname;
        off_t fsize;
        SorterNode* next;
        SorterNode(const string &n, off_t s) : fname(n), fsize(s), next(nullptr) {}
    };
    // Gather into sortable list
    SorterNode* sort_head = nullptr;
    for (auto* n = files.head; n; n = n->next) {
        struct stat st;
        stat(n->val.c_str(), &st);
        auto* sn = new SorterNode(n->val, st.st_size);
        sn->next = sort_head;
        sort_head = sn;
    }
    // Bubble sort, since typically small for directory listing
    for (auto* i = sort_head; i; i = i->next)
    for (auto* j = i->next; j; j = j->next) {
        if (i->fsize > j->fsize) {
            swap(i->fname, j->fname);
            swap(i->fsize, j->fsize);
        }
    }
    // Copy back to files
    files.clear();
    for (auto* n = sort_head; n; ) {
        files.push_back(n->fname);
        auto* del = n;
        n = n->next;
        delete del;
    }
    return files;
}

// ====================== OPTIMIZED DATA STRUCTURES ======================
// No vector used

struct Posting {
    int docID; short freq;
    short positions[MAX_POSTING_POSITIONS];
    int pos_size;
    Posting(int d=0): docID(d), freq(0), pos_size(0) { memset(positions, 0, sizeof(positions)); }
    Posting(const Posting& oth) : docID(oth.docID), freq(oth.freq), pos_size(oth.pos_size) {
        memcpy(positions, oth.positions, sizeof(positions));
    }
    Posting& operator=(const Posting& oth) {
        docID = oth.docID; freq = oth.freq; pos_size = oth.pos_size;
        memcpy(positions, oth.positions, sizeof(positions));
        return *this;
    }
    bool operator==(const Posting& o) const { return docID==o.docID && freq==o.freq && pos_size==o.pos_size; }
};

struct Document {
    string filename, filepath; int totalTokens = 0; long fileSize = 0; string full_content;
    Document() = default;
    Document(Document&& other) noexcept 
        : filename(move(other.filename)), filepath(move(other.filepath)),
          totalTokens(other.totalTokens), fileSize(other.fileSize), full_content(move(other.full_content)) {}
    Document(const Document& oth)
        : filename(oth.filename), filepath(oth.filepath),
          totalTokens(oth.totalTokens), fileSize(oth.fileSize), full_content(oth.full_content) {}
    Document& operator=(const Document& oth) {
        filename = oth.filename; filepath = oth.filepath;
        totalTokens = oth.totalTokens; fileSize = oth.fileSize; full_content = oth.full_content;
        return *this;
    }
};

struct RankedDoc {
    int docID; float score; short totalOccurrences; bool inTitle; bool exactPhraseMatch; float titleBoost;
    RankedDoc() : docID(0), score(0.0f), totalOccurrences(0), 
                  inTitle(false), exactPhraseMatch(false), titleBoost(0.0f) {}
    bool operator<(const RankedDoc& other) const {
        if (exactPhraseMatch != other.exactPhraseMatch) return exactPhraseMatch < other.exactPhraseMatch;
        if (titleBoost != other.titleBoost) return titleBoost < other.titleBoost;
        if (fabs(score - other.score) > 0.0001f) return score < other.score;
        return totalOccurrences < other.totalOccurrences;
    }
};

// ====================== HYPER-OPTIMIZED INVERTED INDEX (No vector!) ======================
class HyperOptimizedIndex {
public:
    // key = word, value = custom LinkedList<Posting>
    unordered_map<string, LinkedList<Posting>> idx;
    unordered_map<string, short> docFreq;
    LinkedList<Document> docs;
    UltraFastTrie trie;

    int total_words_processed = 0, total_files_processed = 0;
    void clear() {
        idx.clear();
        docFreq.clear();
        docs.clear();
        trie.clear();
        total_words_processed = 0;
        total_files_processed = 0;
    }
    void build_from_files(const LinkedList<string> &files) {
        clear();
        int file_ct = 0;
        for (auto* fnode = files.head; fnode; fnode = fnode->next) file_ct++;
        if (!files.head) return;
        cout << "Building optimized index from " << file_ct << " files..." << endl;
        auto start_time = chrono::steady_clock::now();
        unordered_set<string> unique_words_set;
        LinkedList<string> unique_words_vec;
        int docId = 0, files_processed = 0;
        for (auto* node = files.head; node; node = node->next) {
            const string& path = node->val;
            ifstream in(path, ios::binary);
            if (!in.is_open()) continue;
            in.seekg(0, ios::end);
            streamsize fileSize = in.tellg();
            in.seekg(0, ios::beg);
            if (fileSize > 100 * 1024 * 1024) {
                cerr << "Skipping very large file: " << path 
                     << " (" << fileSize/1024/1024 << " MB)" << endl;
                in.close();
                continue;
            }
            string content(fileSize, '\0');
            in.read(&content[0], fileSize);
            in.close();
            string full_content = read_full_file_content(content);
            size_t last_slash = path.find_last_of("/\\");
            string filename = (last_slash == string::npos) ? path : path.substr(last_slash + 1);
            Document doc;
            doc.filename = filename;
            doc.filepath = path;
            doc.fileSize = fileSize;
            doc.full_content = full_content;
            auto tokens = tokenize_ultrafast(full_content);
            {
                int tok_ct = 0;
                for (auto* tn=tokens.head; tn; tn=tn->next) tok_ct++;
                doc.totalTokens = tok_ct;
                total_words_processed += tok_ct;
            }
            unordered_map<string, Posting> local;
            int i=0;
            for (auto* tnode = tokens.head; tnode; tnode = tnode->next, ++i) {
                const string &t = tnode->val;
                if (!local.count(t)) local[t] = Posting(docId);
                Posting &p = local[t];
                if (p.freq < 1000) {
                    p.freq++;
                    if (p.pos_size < MAX_POSTING_POSITIONS)
                        p.positions[p.pos_size++] = i;
                }
                if (unique_words_set.insert(t).second)
                    unique_words_vec.push_back(t);
            }
            // Add all postings to index
            for (auto& kv : local) {
                idx[kv.first].push_back(kv.second);
            }
            docs.push_back(move(doc));
            docId++;
            files_processed++;
            total_files_processed++;
            if (files_processed % 5 == 0) {
                // count unique words
                int uq_ct = 0;
                for (auto* uqn = unique_words_vec.head; uqn; uqn = uqn->next) uq_ct++;
                cout << "Processed " << files_processed << "/" << file_ct << " files, " << uq_ct << " unique words" << endl;
            }
            // 200k unique words: count
            int uq_ct = 0;
            for (auto* uqn = unique_words_vec.head; uqn; uqn = uqn->next) uq_ct++;
            if (uq_ct > 200000) {
                cout << "Reached word limit (200k), stopping early" << endl;
                break;
            }
        }
        cout << "Building Trie from unique words..." << endl;
        // Sort unique_words_vec by length (manual)
        struct StrLenSorterNode { string s; StrLenSorterNode* next; int len; StrLenSorterNode(const string& t): s(t), next(nullptr), len(t.size()) {} };
        StrLenSorterNode* sorthead = nullptr;
        for (auto* n = unique_words_vec.head; n; n = n->next) {
            auto* sn = new StrLenSorterNode(n->val);
            sn->next = sorthead;
            sorthead = sn;
        }
        //bubble
        for (auto* i = sorthead; i; i=i->next)
        for (auto* j=i->next; j; j=j->next)
            if (i->len > j->len) { swap(i->s,j->s); swap(i->len,j->len); }
        int trie_words = 0;
        for (auto* n = sorthead; n; n=n->next) {
            if (n->len>=2&&n->len<=20) { trie.insert(n->s); trie_words++; }
        }
        // cleanup
        for (auto* n=sorthead; n;) { auto* dlt=n; n=n->next; delete dlt; }
        // Set docFreq
        for (auto &kv : idx) {
            int ct=0;
            for(auto* p=kv.second.head;p;p=p->next) ct++;
            docFreq[kv.first] = (short)min(ct, 32767);
        }
        auto end_time = chrono::steady_clock::now();
        auto elapsed = chrono::duration_cast<chrono::milliseconds>(end_time - start_time);
        int ndct = 0; for (auto* d=docs.head;d;d=d->next) ndct++;
        cout << "Index built in " << elapsed.count() << "ms: " << endl;
        cout << "  - Documents: " << ndct << endl;
        cout << "  - Unique terms: " << idx.size() << endl;
        cout << "  - Trie words: " << trie_words << endl;
        cout << "  - Total words processed: " << total_words_processed << endl;
    }
};

// ====================== HYPER-FAST SEARCH ENGINE (No STL vector, except for sort scope) ======================
class HyperFastSearchEngine {
public:
    HyperOptimizedIndex index;
    int Ndocs = 0;
    // Manual search cache
    struct SearchCacheEntry {
        string key;
        LinkedList<RankedDoc> results;
        SearchCacheEntry* next;
    };
    mutable SearchCacheEntry* search_cache_head = nullptr;
    mutable int search_cache_size = 0;
    void clear_search_cache() {
        for (auto* n=search_cache_head; n; ) {
            auto* nxt = n->next;
            delete n;
            n = nxt;
        }
        search_cache_head = nullptr; search_cache_size = 0;
    }
    const LinkedList<RankedDoc>* find_in_cache(const string& key) const {
        for (auto* n=search_cache_head;n;n=n->next) if (n->key==key) return &n->results;
        return nullptr;
    }
    void insert_in_cache(const string& key, LinkedList<RankedDoc>& results) const {
        if (search_cache_size>=1000) {
            auto* old = search_cache_head;
            search_cache_head = search_cache_head->next;
            delete old; search_cache_size--;
        }
        auto* entry = new SearchCacheEntry{key, results, search_cache_head};
        search_cache_head = entry; search_cache_size++;
    }

    void index_folder(const string &dirpath) {
        struct stat info;
        if (stat(dirpath.c_str(), &info) != 0) {
            cerr << "Error: Directory not found: " << dirpath << endl;
            return;
        }
        if (!(info.st_mode & S_IFDIR)) {
            cerr << "Error: Not a directory: " << dirpath << endl;
            return;
        }
        auto files = scan_files_optimized(dirpath);
        int ndoc=0; for(auto* n=files.head;n;n=n->next) ndoc++;
        if (!files.head) {
            cerr << "Warning: No .txt files found in " << dirpath << endl;
            return;
        }
        cout << "Found " << ndoc << " text files to index" << endl;
        index.build_from_files(files);
        int cnt=0; for(auto* n=index.docs.head;n;n=n->next) cnt++;
        Ndocs=cnt;
        clear_search_cache();
    }
    float idf(const string &term) const {
        auto it = index.docFreq.find(term);
        if (it == index.docFreq.end()) return 0.0f;
        short df = it->second;
        if (df == 0 || Ndocs == 0) return 0.0f;
        return log10((float)Ndocs / (float)df + 1.0f);
    }
    int get_total_results_count(const string &query) {
        if (Ndocs == 0) return 0;
        auto all_results = search_with_ranking(query, 1, INT_MAX);
        int cnt=0; for (auto* n=all_results.head;n;n=n->next) cnt++;
        return cnt;
    }
    LinkedList<RankedDoc> search_with_ranking(const string &query, int page, int resultsPerPage) const {
        string cache_key = query + "|PAGE|" + to_string(page) + "|" + to_string(resultsPerPage);
        if (auto* found = find_in_cache(cache_key)) return *found;
        if (Ndocs == 0) {
            LinkedList<RankedDoc> empty; insert_in_cache(cache_key, empty); return empty;
        }
        LinkedList<string> qtokens;
        {
            string lower_query = toLowerFast(query);
            qtokens = tokenize_ultrafast(lower_query);
        }
        if (!qtokens.head) {
            LinkedList<RankedDoc> empty; insert_in_cache(cache_key, empty); return empty;
        }
        string exact_phrase = toLowerFast(query);
        unordered_set<int> exact_phrase_docs;
        int ndidx=0; for(auto* d=index.docs.head;d;d=d->next) ndidx++;
        if (ndidx == 0) { LinkedList<RankedDoc> empty; insert_in_cache(cache_key, empty); return empty; }
        if (qtokens.head && qtokens.head->next) {
            int docID = 0;
            for (auto* d=index.docs.head;d;d=d->next,++docID) {
                string doc_content_lower = toLowerFast(d->val.full_content);
                if (doc_content_lower.find(exact_phrase) != string::npos)
                    exact_phrase_docs.insert(docID);
            }
        }
        unordered_map<int, float> doc_scores;
        unordered_map<int, short> doc_occurrences;
        unordered_map<int, float> title_match_bonus;
        unordered_map<int, bool> has_title_match;
        int docID = 0;
        for (auto* d=index.docs.head;d;d=d->next,++docID) {
            string filename_lower = toLowerFast(d->val.filename);
            float title_score = 0.0f;
            for (auto* t = qtokens.head; t; t=t->next) {
                const string& term = t->val;
                if (term.length() < 3) continue;
                size_t pos = filename_lower.find(term);
                if (pos != string::npos) {
                    float term_score = 1.0f;
                    if ((pos == 0 || !isalnum(filename_lower[pos-1])) &&
                        (pos + term.length() == filename_lower.length() || 
                         !isalnum(filename_lower[pos + term.length()]))) {
                        term_score = 2.0f;
                    }
                    if (pos < 20) term_score *= 1.5f;
                    title_score += term_score;
                    has_title_match[docID] = true;
                }
            }
            if (title_score > 0) title_match_bonus[docID] = title_score;
        }
        unordered_map<string, float> term_idf;
        for (auto* t=qtokens.head;t;t=t->next) term_idf[t->val] = idf(t->val);
        // --- Scoring
        for (auto* t=qtokens.head;t;t=t->next) {
            const string& term = t->val;
            auto it = index.idx.find(term);
            if (it == index.idx.end()) continue;
            float idfv = term_idf[term];
            for (auto* p = it->second.head; p; p = p->next) {
                const Posting& pp = p->val;
                int docID = pp.docID;
                float tf = (float)pp.freq / (1.0f + log(1.0f + index.docs.head->val.totalTokens / 1000.0f));
                float position_weight = 1.0f;
                if (pp.pos_size > 0) {
                    float avg_position = 0;
                    for (int i = 0; i < pp.pos_size; ++i) avg_position += pp.positions[i];
                    avg_position /= pp.pos_size;
                    float doc_len = index.docs.head->val.totalTokens;
                    float position_ratio = avg_position / doc_len;
                    if (position_ratio < 0.2f) position_weight = 1.0f + (0.2f - position_ratio) * 2.0f;
                }
                float base_score = tf * idfv * position_weight;
                if (has_title_match[docID]) base_score *= (10.0f + title_match_bonus[docID] * 5.0f);
                if (exact_phrase_docs.find(docID) != exact_phrase_docs.end()) base_score *= 5.0f;
                if (pp.freq > 10) base_score *= min(1.0f + (float)log((float)pp.freq) / 5.0f, 3.0f);
                doc_scores[docID] += base_score;
                doc_occurrences[docID] += pp.freq;
            }
        }
        // Document length normalization and title boosts
        for (auto& kv : doc_scores) {
            int docID = kv.first;
            int docLength = index.docs.head->val.totalTokens;
            float& score = kv.second;
            if (docLength < 100) score *= 0.1f;
            else if (docLength > 1000 && docLength < 100000) score *= 1.2f;
            else if (docLength > 200000) score *= 0.9f;
            if (has_title_match[docID]) score *= (1.0f + title_match_bonus[docID]);
        }
        // Gather all results, sort and slice by page
        vector<RankedDoc> all_results_raw;
        for (auto& kv : doc_scores) {
            int docID = kv.first;
            if (kv.second <= 0.000001f) continue;
            RankedDoc rd;
            rd.docID = docID;
            rd.score = kv.second;
            rd.totalOccurrences = doc_occurrences[docID];
            rd.inTitle = has_title_match[docID];
            rd.exactPhraseMatch = (exact_phrase_docs.find(docID) != exact_phrase_docs.end());
            rd.titleBoost = has_title_match[docID] ? title_match_bonus[docID] : 0.0f;
            all_results_raw.push_back(rd);
        }
        sort(all_results_raw.begin(), all_results_raw.end(), [](const RankedDoc& a, const RankedDoc& b) {
            return b < a;
        });
        // Build output LinkedList<RankedDoc>
        LinkedList<RankedDoc> results;
        int total_results = all_results_raw.size();
        int start_idx = (page - 1) * resultsPerPage;
        int end_idx = min(start_idx + resultsPerPage, total_results);
        for (int i = start_idx; i < end_idx; ++i) results.push_back(all_results_raw[i]);
        insert_in_cache(cache_key, results);
        return results;
    }
    LinkedList<RankedDoc> search_with_pagination(const string &query, int page=1, int resultsPerPage=10) const {
        return search_with_ranking(query, page, resultsPerPage);
    }
    int get_prefix_total_results_count(const string &prefix, int expandLimit=100) {
        auto sug = autocomplete(prefix, expandLimit);
        int cnt=0; for(auto* n=sug.head;n;n=n->next) cnt++;
        if (!cnt) return 0;
        string query;
        int i = 0;
        for (auto* n = sug.head; n && i < 5; n = n->next, ++i) {
            if (i > 0) query += " ";
            query += n->val;
        }
        return get_total_results_count(query);
    }
    LinkedList<RankedDoc> prefix_search_with_pagination(const string &prefix, int expandLimit=100, int page=1, int resultsPerPage=10) {
        auto sug = autocomplete(prefix, expandLimit);
        int scnt=0; for(auto* n=sug.head;n;n=n->next) scnt++;
        if (!scnt) { LinkedList<RankedDoc> empty; return empty; }
        string query;
        int i=0;
        for(auto* n=sug.head;n&&i<5;n=n->next,++i) {
            if (i>0) query+=" ";
            query+=n->val;
        }
        return search_with_pagination(query, page, resultsPerPage);
    }
    LinkedList<string> autocomplete(const string &prefix, int limit=10) const {
        return index.trie.starts_with(toLowerFast(prefix), limit);
    }
    string get_snippet_for_doc(const LinkedList<string>& query_terms, int docID) const {
        int curr=0;
        for(auto* n=index.docs.head;n;n=n->next,++curr)
            if(curr==docID) return get_snippet_improved(n->val.full_content, query_terms);
        return "";
    }
    string filename_for(int docID) const {
        int curr=0; for(auto* n=index.docs.head;n;n=n->next,++curr)
            if(curr==docID) return n->val.filename;
        return "";
    }
    string filepath_for(int docID) const {
        int curr=0; for(auto* n=index.docs.head;n;n=n->next,++curr)
            if(curr==docID) return n->val.filepath;
        return "";
    }
};

// ====================== MAIN FUNCTION (No vectors/sequence cont) ======================
int main(int argc, char* argv[]) {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);
    string data_dir = "./Data";
    string mode;
    string query;
    string prefix;
    int resultsPerPage = 10;
    int limit = 10;
    int expandLimit = 100;
    int page = 1;
    for (int i = 1; i < argc; i++) {
        string arg = argv[i];
        if (arg == "--data-dir" && i + 1 < argc) data_dir = argv[++i];
        else if (arg == "--search" && i + 1 < argc) {mode = "search"; query = argv[++i];}
        else if (arg == "--autocomplete" && i + 1 < argc) {mode = "autocomplete"; prefix = argv[++i];}
        else if (arg == "--prefixsearch" && i + 1 < argc) {mode = "prefixsearch"; prefix = argv[++i];}
        else if (arg == "--topK" && i + 1 < argc) resultsPerPage = stoi(argv[++i]);
        else if (arg == "--limit" && i + 1 < argc) limit = stoi(argv[++i]);
        else if (arg == "--expandLimit" && i + 1 < argc) expandLimit = stoi(argv[++i]);
        else if (arg == "--page" && i + 1 < argc) page = stoi(argv[++i]);
    }
    HyperFastSearchEngine engine;
    engine.index_folder(data_dir);
    if (engine.Ndocs == 0) {
        json error_json;
        error_json["error"] = "No documents could be indexed.";
        cout << error_json.dump() << endl;
        return 1;
    }
    if (mode == "search") {
        auto start = chrono::steady_clock::now();
        auto results = engine.search_with_pagination(query, page, resultsPerPage);
        int total_results = engine.get_total_results_count(query);
        int total_pages = max(1, (total_results + resultsPerPage - 1) / resultsPerPage);
        auto end = chrono::steady_clock::now();
        auto elapsed = chrono::duration_cast<chrono::milliseconds>(end - start);
        json output_json;
        output_json["query"] = query;
        int rct=0; for(auto* n=results.head;n;n=n->next) rct++;
        output_json["count"] = rct;
        output_json["total_results"] = total_results;
        output_json["total_pages"] = total_pages;
        output_json["page"] = page;
        output_json["results_per_page"] = resultsPerPage;
        output_json["mode"] = "search";
        output_json["time_ms"] = elapsed.count();
        if (page < total_pages) output_json["next_page"] = page + 1;
        if (page > 1) output_json["prev_page"] = page - 1;
        LinkedList<string> query_terms = tokenize_ultrafast(toLowerFast(query));
        json results_json = json::array();
        int start_rank = (page - 1) * resultsPerPage + 1;
        int i = 0;
        for (auto* n = results.head; n; n=n->next,++i) {
            const auto& rd = n->val;
            json result_item;
            result_item["rank"] = start_rank + i;
            result_item["filename"] = engine.filename_for(rd.docID);
            result_item["filepath"] = engine.filepath_for(rd.docID);
            result_item["score"] = rd.score;
            result_item["totalOccurrences"] = rd.totalOccurrences;
            result_item["inTitle"] = rd.inTitle;
            result_item["exactPhraseMatch"] = rd.exactPhraseMatch;
            result_item["snippet"] = engine.get_snippet_for_doc(query_terms, rd.docID);
            results_json.push_back(result_item);
        }
        output_json["results"] = results_json;
        cout << output_json.dump() << endl;
    } else if (mode == "autocomplete") {
        auto start = chrono::steady_clock::now();
        auto suggestions = engine.autocomplete(prefix, limit);
        auto end = chrono::steady_clock::now();
        auto elapsed = chrono::duration_cast<chrono::milliseconds>(end - start);
        json output_json;
        output_json["prefix"] = prefix;
        int scnt=0; for(auto* n=suggestions.head;n;n=n->next) scnt++;
        output_json["count"] = scnt;
        output_json["time_ms"] = elapsed.count();
        // Convert the linked list to vector for json output
        vector<string> sug_for_json;
        for (auto* n = suggestions.head; n; n = n->next) sug_for_json.push_back(n->val);
        output_json["suggestions"] = sug_for_json;
        cout << output_json.dump() << endl;
    } else if (mode == "prefixsearch") {
        auto start = chrono::steady_clock::now();
        auto results = engine.prefix_search_with_pagination(prefix, expandLimit, page, resultsPerPage);
        int total_results = engine.get_prefix_total_results_count(prefix, expandLimit);
        int total_pages = max(1, (total_results + resultsPerPage - 1) / resultsPerPage);
        auto end = chrono::steady_clock::now();
        auto elapsed = chrono::duration_cast<chrono::milliseconds>(end - start);
        json output_json;
        output_json["prefix"] = prefix;
        int rct=0; for(auto* n=results.head;n;n=n->next) rct++;
        output_json["count"] = rct;
        output_json["total_results"] = total_results;
        output_json["total_pages"] = total_pages;
        output_json["page"] = page;
        output_json["results_per_page"] = resultsPerPage;
        output_json["mode"] = "prefix_search";
        output_json["time_ms"] = elapsed.count();
        if (page < total_pages) output_json["next_page"] = page + 1;
        if (page > 1) output_json["prev_page"] = page - 1;
        // for prefix query term, just single
        LinkedList<string> query_terms; query_terms.push_back(prefix);
        json results_json = json::array();
        int start_rank = (page - 1) * resultsPerPage + 1;
        int i = 0;
        for (auto* n = results.head; n; n = n->next, ++i) {
            const auto& rd = n->val;
            json result_item;
            result_item["rank"] = start_rank + i;
            result_item["filename"] = engine.filename_for(rd.docID);
            result_item["filepath"] = engine.filepath_for(rd.docID);
            result_item["score"] = rd.score;
            result_item["totalOccurrences"] = rd.totalOccurrences;
            result_item["inTitle"] = rd.inTitle;
            result_item["exactPhraseMatch"] = rd.exactPhraseMatch;
            result_item["snippet"] = engine.get_snippet_for_doc(query_terms, rd.docID);
            results_json.push_back(result_item);
        }
        output_json["results"] = results_json;
        cout << output_json.dump() << endl;
    } else {
        json status_json;
        status_json["status"] = "ready";
        int nd=0; for(auto* n=engine.index.docs.head;n;n=n->next) nd++;
        status_json["documents"] = nd;
        status_json["unique_terms"] = (int)engine.index.idx.size();
        status_json["data_directory"] = data_dir;
        status_json["total_words_indexed"] = engine.index.total_words_processed;
        cout << status_json.dump() << endl;
    }
    return 0;
}