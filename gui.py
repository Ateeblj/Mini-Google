#!/usr/bin/env python3
"""
Mini Google GUI - Clean Version with Trie Focus + Search History + Pagination
"""
import sys
import json
import subprocess
import os
from PyQt5 import QtWidgets, QtCore, QtGui
from collections import deque
import datetime

# CONFIGURATION
EXECUTABLE = "minigoog.exe"  # Your C++ executable
DATA_DIR = "Data"            # Your data folder
MAX_HISTORY = 10             # Maximum number of searches to keep

class CircularQueue:
    """Circular queue for storing search history"""
    def __init__(self, max_size=10):
        self.queue = deque(maxlen=max_size)
        self.max_size = max_size
    
    def add(self, query, timestamp=None):
        """Add a search to history"""
        if not query or not query.strip():
            return
        
        if timestamp is None:
            timestamp = datetime.datetime.now()
        
        entry = {
            'query': query.strip(),
            'timestamp': timestamp,
            'time_str': timestamp.strftime("%H:%M:%S")
        }
        
        # Check if same query already exists (remove it first)
        for i, item in enumerate(self.queue):
            if item['query'].lower() == query.strip().lower():
                del self.queue[i]
                break
        
        self.queue.append(entry)
    
    def get_all(self):
        """Get all history entries (newest first)"""
        return list(reversed(self.queue))
    
    def clear(self):
        """Clear all history"""
        self.queue.clear()
    
    def get_recent(self, count=5):
        """Get most recent searches"""
        return list(reversed(self.queue))[:count]
    
    def size(self):
        """Get current size"""
        return len(self.queue)
    
    def is_empty(self):
        """Check if empty"""
        return len(self.queue) == 0
    
    def __len__(self):
        return len(self.queue)

def run_command(args):
    """Run command and return output"""
    try:
        result = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=15,
            shell=False
        )
        
        if result.returncode != 0:
            return None, f"Error {result.returncode}: {result.stderr[:200]}"
        
        return result.stdout.strip(), None
        
    except subprocess.TimeoutExpired:
        return None, "Command timed out after 15 seconds"
    except Exception as e:
        return None, f"Exception: {str(e)}"

def clean_cpp_output(output):
    """Clean C++ output to extract JSON only"""
    if not output:
        return output
    
    # Split into lines
    lines = output.strip().split('\n')
    
    # Find the JSON part (starts with { or [)
    json_lines = []
    in_json = False
    
    for line in lines:
        stripped = line.strip()
        
        # Skip common debug lines
        if (stripped.startswith("=== ") or 
            stripped.startswith("Data directory:") or
            stripped.startswith("Scanning directory:") or
            stripped.startswith("  Found:") or
            stripped.startswith("Indexed ") or
            stripped.startswith("✅ ") or
            stripped.startswith("☑ ") or
            stripped.startswith("☐ ") or
            stripped.startswith("Autocomplete for:") or
            stripped.startswith("Suggestions (") or
            stripped.startswith("Prefix search for:") or
            stripped.startswith("Searching for:") or
            stripped.startswith("Found ") and "results:" in stripped or
            stripped.startswith("Operation completed successfully.")):
            continue
        
        # Look for JSON start
        if stripped.startswith('{') or stripped.startswith('['):
            in_json = True
        
        if in_json:
            json_lines.append(line)
    
    # If we found JSON lines, return them
    if json_lines:
        return '\n'.join(json_lines)
    
    # Otherwise, try to find any line that looks like JSON
    for line in lines:
        stripped = line.strip()
        if stripped and (stripped.startswith('{') or stripped.startswith('[') or stripped.startswith('"')):
            return stripped
    
    # If nothing found, return original but clean debug lines
    clean_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not (stripped.startswith("=== ") or stripped.startswith("Data directory:")):
            clean_lines.append(stripped)
    
    return '\n'.join(clean_lines)

class MiniGoogleGUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🌳 Trie Search Engine")
        self.setGeometry(100, 100, 1100, 800)
        
        # Initialize search history
        self.search_history = CircularQueue(max_size=MAX_HISTORY)
        
        # Pagination variables
        self.current_page = 1
        self.total_pages = 1
        self.total_results = 0
        self.current_query = ""
        self.current_mode = "prefix"
        self.results_per_page = 50  # Default results per page
        
        self.init_ui()
        self.check_backend()
        
    def init_ui(self):
        # Central widget
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header_widget = QtWidgets.QWidget()
        header_layout = QtWidgets.QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 10)
        
        title = QtWidgets.QLabel("🌲 Trie-Based Search Engine")
        title.setStyleSheet("""
            font-size: 32px;
            font-weight: bold;
            color: #1a73e8;
            padding: 10px;
        """)
        title.setAlignment(QtCore.Qt.AlignCenter)
        header_layout.addWidget(title)
        
        subtitle = QtWidgets.QLabel("Type to see Trie suggestions • Double-click to search • Google-style pagination")
        subtitle.setStyleSheet("""
            font-size: 14px;
            color: #5f6368;
            padding: 5px;
        """)
        subtitle.setAlignment(QtCore.Qt.AlignCenter)
        subtitle.setWordWrap(True)
        header_layout.addWidget(subtitle)
        
        main_layout.addWidget(header_widget)
        
        # Search box
        search_container = QtWidgets.QWidget()
        search_layout = QtWidgets.QHBoxLayout(search_container)
        search_layout.setContentsMargins(50, 0, 50, 0)
        
        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("Start typing to see Trie suggestions...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                font-size: 18px;
                padding: 15px;
                border: 2px solid #dfe1e5;
                border-radius: 30px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #34a853;
                border-width: 3px;
            }
        """)
        self.search_input.setMinimumHeight(55)
        search_layout.addWidget(self.search_input, 5)
        
        self.search_button = QtWidgets.QPushButton("🔍 Search")
        self.search_button.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                padding: 15px 30px;
                background-color: #4285f4;
                color: white;
                border: none;
                border-radius: 30px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3367d6;
            }
            QPushButton:pressed {
                background-color: #2a56c6;
            }
        """)
        self.search_button.setMinimumHeight(55)
        self.search_button.setMinimumWidth(120)
        self.search_button.clicked.connect(self.do_search)
        search_layout.addWidget(self.search_button, 1)
        
        main_layout.addWidget(search_container)
        
        # Mode selector and history button
        mode_history_widget = QtWidgets.QWidget()
        mode_history_layout = QtWidgets.QHBoxLayout(mode_history_widget)
        mode_history_layout.setContentsMargins(50, 5, 50, 5)
        
        # Mode selector
        mode_label = QtWidgets.QLabel("Search Mode:")
        mode_label.setStyleSheet("font-weight: bold; color: #5f6368; font-size: 14px;")
        mode_history_layout.addWidget(mode_label)
        
        self.search_mode = QtWidgets.QComboBox()
        self.search_mode.addItems([
            "🌳 Prefix Search (Trie expands your word)",
            "🔍 Exact Search",
            "💡 Suggestions Only"
        ])
        self.search_mode.setStyleSheet("""
            QComboBox {
                font-size: 14px;
                padding: 8px;
                border: 1px solid #dfe1e5;
                border-radius: 8px;
                background-color: white;
            }
            QComboBox:hover {
                border-color: #4285f4;
            }
        """)
        self.search_mode.currentIndexChanged.connect(self.on_mode_changed)
        mode_history_layout.addWidget(self.search_mode, 2)
        
        # Results per page selector
        results_per_page_label = QtWidgets.QLabel("Results/page:")
        results_per_page_label.setStyleSheet("font-weight: bold; color: #5f6368; font-size: 14px;")
        mode_history_layout.addWidget(results_per_page_label)
        
        self.results_per_page_combo = QtWidgets.QComboBox()
        self.results_per_page_combo.addItems(["10", "20", "50", "100"])
        self.results_per_page_combo.setCurrentText("50")
        self.results_per_page_combo.setStyleSheet("""
            QComboBox {
                font-size: 14px;
                padding: 8px;
                border: 1px solid #dfe1e5;
                border-radius: 8px;
                background-color: white;
            }
            QComboBox:hover {
                border-color: #4285f4;
            }
        """)
        mode_history_layout.addWidget(self.results_per_page_combo)
        
        # History button
        self.history_button = QtWidgets.QPushButton("📜 History")
        self.history_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                padding: 8px 15px;
                background-color: #f1f3f4;
                color: #5f6368;
                border: 1px solid #dadce0;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #e8eaed;
                border-color: #4285f4;
            }
        """)
        self.history_button.setToolTip("Show search history")
        self.history_button.clicked.connect(self.show_history)
        mode_history_layout.addWidget(self.history_button)
        
        # Clear history button
        self.clear_history_button = QtWidgets.QPushButton("🗑️ Clear")
        self.clear_history_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                padding: 8px 15px;
                background-color: #fce8e6;
                color: #d93025;
                border: 1px solid #fad2cf;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #f9c9c5;
                border-color: #d93025;
            }
        """)
        self.clear_history_button.setToolTip("Clear search history")
        self.clear_history_button.clicked.connect(self.clear_history)
        mode_history_layout.addWidget(self.clear_history_button)
        
        mode_history_layout.addStretch()
        main_layout.addWidget(mode_history_widget)
        
        # Pagination controls
        pagination_widget = QtWidgets.QWidget()
        pagination_layout = QtWidgets.QHBoxLayout(pagination_widget)
        pagination_layout.setContentsMargins(50, 5, 50, 5)
        
        # Previous button
        self.prev_button = QtWidgets.QPushButton("◀ Previous")
        self.prev_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                padding: 8px 15px;
                background-color: #f1f3f4;
                color: #5f6368;
                border: 1px solid #dadce0;
                border-radius: 8px;
            }
            QPushButton:hover:enabled {
                background-color: #4285f4;
                color: white;
                border-color: #4285f4;
            }
            QPushButton:disabled {
                color: #bdc1c6;
                background-color: #f8f9fa;
            }
        """)
        self.prev_button.clicked.connect(self.prev_page)
        self.prev_button.setEnabled(False)
        pagination_layout.addWidget(self.prev_button)
        
        # Page info
        self.page_label = QtWidgets.QLabel("Page 1 of 1")
        self.page_label.setStyleSheet("""
            font-size: 14px;
            color: #5f6368;
            font-weight: bold;
            padding: 8px 15px;
        """)
        pagination_layout.addWidget(self.page_label)
        
        # Results info
        self.results_label = QtWidgets.QLabel("0 results")
        self.results_label.setStyleSheet("""
            font-size: 14px;
            color: #70757a;
            padding: 8px 15px;
        """)
        pagination_layout.addWidget(self.results_label)
        
        # Page number input
        self.page_input = QtWidgets.QLineEdit()
        self.page_input.setFixedWidth(50)
        self.page_input.setStyleSheet("""
            QLineEdit {
                font-size: 14px;
                padding: 5px;
                border: 1px solid #dadce0;
                border-radius: 4px;
                text-align: center;
            }
            QLineEdit:focus {
                border-color: #4285f4;
            }
        """)
        self.page_input.returnPressed.connect(self.go_to_page)
        pagination_layout.addWidget(self.page_input)
        
        self.total_pages_label = QtWidgets.QLabel("of 1")
        self.total_pages_label.setStyleSheet("font-size: 14px; color: #5f6368; padding: 5px;")
        pagination_layout.addWidget(self.total_pages_label)
        
        # Next button
        self.next_button = QtWidgets.QPushButton("Next ▶")
        self.next_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                padding: 8px 15px;
                background-color: #f1f3f4;
                color: #5f6368;
                border: 1px solid #dadce0;
                border-radius: 8px;
            }
            QPushButton:hover:enabled {
                background-color: #4285f4;
                color: white;
                border-color: #4285f4;
            }
            QPushButton:disabled {
                color: #bdc1c6;
                background-color: #f8f9fa;
            }
        """)
        self.next_button.clicked.connect(self.next_page)
        self.next_button.setEnabled(False)
        pagination_layout.addWidget(self.next_button)
        
        # Go button
        self.go_button = QtWidgets.QPushButton("Go")
        self.go_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                padding: 8px 15px;
                background-color: #f1f3f4;
                color: #4285f4;
                border: 1px solid #dadce0;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e8f0fe;
                border-color: #4285f4;
            }
        """)
        self.go_button.setFixedWidth(60)
        self.go_button.clicked.connect(self.go_to_page)
        pagination_layout.addWidget(self.go_button)
        
        pagination_layout.addStretch()
        main_layout.addWidget(pagination_widget)
        
        # Status
        self.status_label = QtWidgets.QLabel("Ready - Trie is waiting for your input...")
        self.status_label.setStyleSheet("""
            font-size: 13px;
            color: #5f6368;
            padding: 8px;
            background-color: #f1f3f4;
            border-radius: 8px;
            margin: 0px 50px;
        """)
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        # Main splitter
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        
        # LEFT PANEL: Trie Suggestions
        left_panel = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        
        # Trie header
        trie_header = QtWidgets.QLabel("🌳 TRIE SUGGESTIONS")
        trie_header.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #34a853;
            padding: 12px;
            background-color: #e6f4ea;
            border-radius: 10px;
            border-left: 5px solid #34a853;
        """)
        trie_header.setAlignment(QtCore.Qt.AlignCenter)
        left_layout.addWidget(trie_header)
        
        # Trie explanation
        trie_explain = QtWidgets.QLabel(
            "The <b>Trie data structure</b> provides instant word suggestions as you type.\n"
            "Each character you type traverses the tree to find matching words."
        )
        trie_explain.setStyleSheet("""
            font-size: 13px;
            color: #5f6368;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 8px;
        """)
        trie_explain.setWordWrap(True)
        trie_explain.setAlignment(QtCore.Qt.AlignCenter)
        left_layout.addWidget(trie_explain)
        
        # Suggestions list
        self.suggestions_list = QtWidgets.QListWidget()
        self.suggestions_list.setStyleSheet("""
            QListWidget {
                font-size: 14px;
                border: 2px solid #e8f0fe;
                border-radius: 10px;
                background-color: white;
            }
            QListWidget::item {
                padding: 12px;
                border-bottom: 1px solid #f1f3f4;
                font-size: 15px;
            }
            QListWidget::item:hover {
                background-color: #e8f0fe;
                color: #1a73e8;
            }
            QListWidget::item:selected {
                background-color: #1a73e8;
                color: white;
                font-weight: bold;
            }
        """)
        self.suggestions_list.itemDoubleClicked.connect(self.use_suggestion)
        left_layout.addWidget(self.suggestions_list, 1)
        
        # Trie stats
        self.trie_stats = QtWidgets.QLabel("Type above to see Trie magic...")
        self.trie_stats.setStyleSheet("""
            font-size: 12px;
            color: #70757a;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 8px;
            border: 1px solid #dadce0;
        """)
        self.trie_stats.setAlignment(QtCore.Qt.AlignCenter)
        left_layout.addWidget(self.trie_stats)
        
        splitter.addWidget(left_panel)
        
        # RIGHT PANEL: Results
        right_panel = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 5, 5, 5)
        
        # Results header
        results_header = QtWidgets.QLabel("📄 SEARCH RESULTS")
        results_header.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #1a73e8;
            padding: 12px;
            background-color: #e8f0fe;
            border-radius: 10px;
            border-left: 5px solid #1a73e8;
        """)
        results_header.setAlignment(QtCore.Qt.AlignCenter)
        right_layout.addWidget(results_header)
        
        # Results explanation
        results_explain = QtWidgets.QLabel(
            "Results are ranked using <b>Priority Queue/Heap</b> algorithm.\n"
            "Higher scores indicate better relevance based on term frequency, title matches, and file size."
        )
        results_explain.setStyleSheet("""
            font-size: 13px;
            color: #5f6368;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 8px;
        """)
        results_explain.setWordWrap(True)
        results_explain.setAlignment(QtCore.Qt.AlignCenter)
        right_layout.addWidget(results_explain)
        
        # Results display
        self.results_display = QtWidgets.QTextEdit()
        self.results_display.setStyleSheet("""
            QTextEdit {
                font-size: 14px;
                border: 2px solid #dfe1e5;
                border-radius: 10px;
                background-color: white;
                padding: 10px;
            }
        """)
        self.results_display.setReadOnly(True)
        right_layout.addWidget(self.results_display, 1)
        
        splitter.addWidget(right_panel)
        
        # Set initial sizes (Trie panel bigger)
        splitter.setSizes([400, 600])
        
        main_layout.addWidget(splitter, 1)
        
        # Page number navigation (like Google)
        self.page_numbers_widget = QtWidgets.QWidget()
        self.page_numbers_layout = QtWidgets.QHBoxLayout(self.page_numbers_widget)
        self.page_numbers_layout.setContentsMargins(50, 5, 50, 5)
        self.page_numbers_layout.setAlignment(QtCore.Qt.AlignCenter)
        self.page_numbers = []  # Store page buttons
        main_layout.addWidget(self.page_numbers_widget)
        
        # Footer with history info
        footer_text = f"""
        💡 Trie provides instant suggestions • Priority Queue ranks results • 
        Double-click suggestion to search • Google-style pagination • History stores last {MAX_HISTORY} searches
        """
        footer = QtWidgets.QLabel(footer_text)
        footer.setStyleSheet("""
            font-size: 12px;
            color: #70757a;
            padding: 10px;
            border-top: 1px solid #dadce0;
            margin-top: 10px;
        """)
        footer.setAlignment(QtCore.Qt.AlignCenter)
        footer.setWordWrap(True)
        main_layout.addWidget(footer)
        
        # Connect signals
        self.search_input.returnPressed.connect(self.do_search)
        self.search_input.textChanged.connect(self.on_text_changed)
        
        # Timer for delayed suggestions
        self.suggestion_timer = QtCore.QTimer()
        self.suggestion_timer.setSingleShot(True)
        self.suggestion_timer.timeout.connect(self.get_suggestions)
        
        # Initialize mode
        self.on_mode_changed(0)
    
    def on_mode_changed(self, index):
        """Handle search mode change"""
        modes = {
            0: "prefix",
            1: "exact", 
            2: "suggestions"
        }
        self.current_mode = modes.get(index, "prefix")
        
        # Update placeholder text
        if self.current_mode == "prefix":
            self.search_input.setPlaceholderText("Type a prefix (Trie will expand it)...")
            self.status_label.setText("🌳 Prefix Search Mode - Trie will expand your prefix")
        elif self.current_mode == "exact":
            self.search_input.setPlaceholderText("Type exact query to search...")
            self.status_label.setText("🔍 Exact Search Mode")
        else:
            self.search_input.setPlaceholderText("Type to see Trie suggestions only...")
            self.status_label.setText("💡 Suggestions Only Mode")
    
    def check_backend(self):
        """Check if C++ backend is working"""
        self.status_label.setText("Connecting to Trie search engine...")
        QtWidgets.QApplication.processEvents()
        
        try:
            # Test with a simple query
            args = [EXECUTABLE, "--data-dir", DATA_DIR, "--autocomplete", "test", "--limit", "1"]
            output, error = run_command(args)
            
            if error:
                self.status_label.setText(f"⚠️ Backend issue: {error[:50]}...")
            else:
                # Clean the output
                clean_output = clean_cpp_output(output)
                if clean_output and ('{' in clean_output or '[' in clean_output):
                    self.status_label.setText("✅ Connected! Start typing to see Trie suggestions...")
                else:
                    self.status_label.setText("⚠️ Backend responded but output format unexpected")
                
        except Exception as e:
            self.status_label.setText(f"❌ Connection error: {str(e)[:50]}...")
    
    def on_text_changed(self, text):
        """Handle text changes for autocomplete"""
        text = text.strip()
        
        # Clear suggestions if empty
        if not text:
            self.suggestions_list.clear()
            self.trie_stats.setText("Type above to see Trie suggestions...")
            return
        
        # Update status
        self.status_label.setText(f"Querying Trie for '{text}'...")
        
        # Start timer for suggestions
        self.suggestion_timer.start(300)
    
    def get_suggestions(self):
        """Get autocomplete suggestions from Trie"""
        query = self.search_input.text().strip()
        if not query:
            return
        
        # Get suggestions
        args = [EXECUTABLE, "--data-dir", DATA_DIR, "--autocomplete", query, "--limit", "15"]
        output, error = run_command(args)
        
        self.suggestions_list.clear()
        
        if error:
            self.suggestions_list.addItem(f"❌ Error: {error[:50]}")
            self.trie_stats.setText(f"Error getting suggestions")
            self.status_label.setText(f"⚠️ Error: {error[:50]}")
            return
        
        # Clean the output first
        clean_output = clean_cpp_output(output)
        
        if not clean_output:
            self.suggestions_list.addItem("No suggestions found")
            self.trie_stats.setText(f"No suggestions for '{query}'")
            self.status_label.setText(f"ℹ️ No suggestions for '{query}'")
            return
        
        try:
            # Try to parse as JSON
            data = json.loads(clean_output)
            suggestions = data.get("suggestions", [])
            
            if suggestions:
                for suggestion in suggestions:
                    if isinstance(suggestion, str) and suggestion.strip():
                        self.suggestions_list.addItem(suggestion.strip())
                
                count = self.suggestions_list.count()
                if count > 0:
                    self.trie_stats.setText(f"🌳 Trie found {count} suggestions for '{query}'")
                    self.status_label.setText(f"✅ Trie suggests {count} words for '{query}'")
                    
                    # Auto-select first item
                    self.suggestions_list.setCurrentRow(0)
                else:
                    self.suggestions_list.addItem("No suggestions found")
                    self.trie_stats.setText(f"No suggestions for '{query}'")
                    self.status_label.setText(f"ℹ️ No suggestions for '{query}'")
            else:
                self.suggestions_list.addItem("No suggestions found")
                self.trie_stats.setText(f"No suggestions for '{query}'")
                self.status_label.setText(f"ℹ️ No suggestions for '{query}'")
                
        except json.JSONDecodeError:
            # If not JSON, try to extract suggestions from raw output
            suggestions_found = False
            
            # Look for numbered suggestions (1. word, 2. word, etc.)
            lines = output.strip().split('\n')
            for line in lines:
                line = line.strip()
                
                # Skip debug lines
                if (line.startswith("=== ") or line.startswith("Data directory:") or 
                    line.startswith("Scanning directory:") or line.startswith("  Found:") or
                    line.startswith("Indexed ") or line.startswith("Autocomplete for:") or
                    line.startswith("Suggestions (") or line.startswith("✅ ") or
                    line.startswith("☑ ") or line.startswith("☐ ")):
                    continue
                
                # Check for numbered items
                if line and (line[0].isdigit() and '. ' in line):
                    # Extract suggestion after number
                    parts = line.split('. ', 1)
                    if len(parts) > 1 and parts[1].strip():
                        self.suggestions_list.addItem(parts[1].strip())
                        suggestions_found = True
                # Check for plain words
                elif line and line.isalpha() and len(line) > 1:
                    self.suggestions_list.addItem(line)
                    suggestions_found = True
            
            if suggestions_found:
                count = self.suggestions_list.count()
                self.trie_stats.setText(f"Found {count} suggestions for '{query}'")
                self.status_label.setText(f"✅ Found {count} suggestions")
                self.suggestions_list.setCurrentRow(0)
            else:
                # Last attempt: just show any non-empty lines that aren't debug
                debug_prefixes = ["===", "Data", "Scanning", "Found:", "Indexed", 
                                "Autocomplete", "Suggestions", "✅", "☑", "☐", "Operation"]
                for line in lines:
                    line = line.strip()
                    if line and not any(line.startswith(prefix) for prefix in debug_prefixes):
                        self.suggestions_list.addItem(line)
                
                if self.suggestions_list.count() > 0:
                    count = self.suggestions_list.count()
                    self.trie_stats.setText(f"Found {count} items")
                    self.status_label.setText(f"Found {count} items")
                else:
                    self.suggestions_list.addItem("No suggestions found")
                    self.trie_stats.setText("No suggestions found")
                    self.status_label.setText("No suggestions found")
        
        except Exception as e:
            self.suggestions_list.addItem(f"Error: {str(e)[:50]}")
            self.trie_stats.setText("Error parsing output")
            self.status_label.setText("Error parsing suggestions")
    
    def use_suggestion(self, item):
        """Use suggestion from list"""
        suggestion = item.text()
        self.search_input.setText(suggestion)
        
        # If not in suggestions-only mode, do search
        if self.current_mode != "suggestions":
            self.do_search()
    
    def do_search(self):
        """Perform search and add to history"""
        query = self.search_input.text().strip()
        if not query:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please enter a search query")
            return
        
        # Reset to page 1 for new search
        self.current_page = 1
        self.perform_search(query, 1)
    
    def perform_search(self, query, page=1):
        """Perform search with pagination"""
        if not query:
            return
        
        # Get results per page from dropdown
        results_per_page = int(self.results_per_page_combo.currentText())
        
        # Store current query
        self.current_query = query
        
        # Add to search history (only first page)
        if page == 1:
            self.search_history.add(query)
        
        # Clear and show searching status
        self.results_display.clear()
        self.status_label.setText(f"🔍 Searching for '{query}' (Page {page})...")
        QtWidgets.QApplication.processEvents()
        
        # Use dynamic results per page
        if self.current_mode == "prefix":
            args = [EXECUTABLE, "--data-dir", DATA_DIR, "--prefixsearch", query, 
                   "--topK", str(results_per_page), "--expandLimit", "100", "--page", str(page)]
        elif self.current_mode == "exact":
            args = [EXECUTABLE, "--data-dir", DATA_DIR, "--search", query, 
                   "--topK", str(results_per_page), "--page", str(page)]
        else:  # suggestions only
            return
        
        output, error = run_command(args)
        
        if error:
            self.results_display.setPlainText(f"SEARCH ERROR\n{'='*60}\n\n{error}")
            self.status_label.setText(f"❌ Search failed")
            return
        
        self.display_results(output, query, page, results_per_page)
    
    def display_results(self, output, query, page=1, results_per_page=50):
        """Display search results with pagination"""
        # Clean the output first
        clean_output = clean_cpp_output(output)
        
        if not clean_output:
            self.results_display.setPlainText(f"No output received from search engine")
            self.status_label.setText("⚠️ No output received")
            return
        
        try:
            data = json.loads(clean_output)
            results = data.get("results", [])
            count = data.get("count", 0)
            total_results = data.get("total_results", count)
            total_pages = data.get("total_pages", 1)
            
            # Update pagination variables
            self.total_results = total_results
            self.total_pages = total_pages
            self.current_page = page
            
            # Build HTML with pagination header
            html = self.build_results_html(results, query, count, page, total_results, total_pages, results_per_page)
            self.results_display.setHtml(html)
            
            # Update pagination UI
            self.update_pagination_ui()
            
            # Generate page number buttons
            self.create_page_number_buttons()
            
            if count > 0:
                start_num = (page - 1) * results_per_page + 1
                end_num = min(start_num + count - 1, total_results)
                self.status_label.setText(f"✅ Page {page}/{total_pages}: Showing results {start_num}-{end_num} of {total_results} for '{query}'")
            else:
                self.status_label.setText(f"ℹ️ No results found for '{query}'")
                
        except json.JSONDecodeError:
            # If not JSON, show raw cleaned output
            self.results_display.setPlainText(f"CLEANED OUTPUT (Non-JSON)\n{'='*60}\n\n{clean_output}")
            self.status_label.setText("⚠️ Received non-JSON output")
        except Exception as e:
            self.results_display.setPlainText(f"ERROR\n{'='*60}\n\n{str(e)}\n\nOriginal Output:\n{output}\n\nCleaned Output:\n{clean_output}")
            self.status_label.setText(f"❌ Error: {str(e)[:50]}")
    
    def update_pagination_ui(self):
        """Update page navigation UI"""
        self.page_label.setText(f"Page {self.current_page} of {self.total_pages}")
        self.results_label.setText(f"{self.total_results} results")
        self.page_input.setText(str(self.current_page))
        self.total_pages_label.setText(f"of {self.total_pages}")
        
        # Enable/disable buttons
        self.prev_button.setEnabled(self.current_page > 1)
        self.next_button.setEnabled(self.current_page < self.total_pages)
    
    def create_page_number_buttons(self):
        """Create page number buttons like Google"""
        # Clear existing buttons
        for button in self.page_numbers:
            self.page_numbers_layout.removeWidget(button)
            button.setParent(None)
        self.page_numbers.clear()
        
        # Don't create buttons if only 1 page
        if self.total_pages <= 1:
            return
        
        # Calculate range of pages to show (like Google: current +/- 2)
        start_page = max(1, self.current_page - 2)
        end_page = min(self.total_pages, self.current_page + 2)
        
        # Ensure we show at least 5 pages if possible
        if end_page - start_page + 1 < 5:
            if start_page == 1:
                end_page = min(self.total_pages, start_page + 4)
            elif end_page == self.total_pages:
                start_page = max(1, end_page - 4)
        
        # Add "First" button if not showing page 1
        if start_page > 1:
            first_btn = QtWidgets.QPushButton("1")
            first_btn.setFixedSize(35, 35)
            first_btn.setStyleSheet("""
                QPushButton {
                    font-size: 14px;
                    color: #4285f4;
                    border: 1px solid #dadce0;
                    border-radius: 4px;
                    background-color: white;
                }
                QPushButton:hover {
                    background-color: #e8f0fe;
                }
            """)
            first_btn.clicked.connect(lambda: self.go_to_specific_page(1))
            self.page_numbers_layout.addWidget(first_btn)
            self.page_numbers.append(first_btn)
            
            # Add ellipsis if needed
            if start_page > 2:
                ellipsis = QtWidgets.QLabel("...")
                ellipsis.setStyleSheet("font-size: 14px; color: #5f6368; padding: 5px;")
                self.page_numbers_layout.addWidget(ellipsis)
        
        # Add page number buttons
        for page_num in range(start_page, end_page + 1):
            btn = QtWidgets.QPushButton(str(page_num))
            btn.setFixedSize(35, 35)
            
            if page_num == self.current_page:
                btn.setStyleSheet("""
                    QPushButton {
                        font-size: 14px;
                        font-weight: bold;
                        color: white;
                        background-color: #4285f4;
                        border: 1px solid #4285f4;
                        border-radius: 4px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        font-size: 14px;
                        color: #4285f4;
                        border: 1px solid #dadce0;
                        border-radius: 4px;
                        background-color: white;
                    }
                    QPushButton:hover {
                        background-color: #e8f0fe;
                    }
                """)
            
            btn.clicked.connect(lambda checked, p=page_num: self.go_to_specific_page(p))
            self.page_numbers_layout.addWidget(btn)
            self.page_numbers.append(btn)
        
        # Add "Last" button if not showing last page
        if end_page < self.total_pages:
            # Add ellipsis if needed
            if end_page < self.total_pages - 1:
                ellipsis = QtWidgets.QLabel("...")
                ellipsis.setStyleSheet("font-size: 14px; color: #5f6368; padding: 5px;")
                self.page_numbers_layout.addWidget(ellipsis)
            
            last_btn = QtWidgets.QPushButton(str(self.total_pages))
            last_btn.setFixedSize(35, 35)
            last_btn.setStyleSheet("""
                QPushButton {
                    font-size: 14px;
                    color: #4285f4;
                    border: 1px solid #dadce0;
                    border-radius: 4px;
                    background-color: white;
                }
                QPushButton:hover {
                    background-color: #e8f0fe;
                }
            """)
            last_btn.clicked.connect(lambda: self.go_to_specific_page(self.total_pages))
            self.page_numbers_layout.addWidget(last_btn)
            self.page_numbers.append(last_btn)
    
    def go_to_specific_page(self, page_num):
        """Go to specific page number"""
        if 1 <= page_num <= self.total_pages and page_num != self.current_page:
            self.current_page = page_num
            self.perform_search(self.current_query, page_num)
    
    def prev_page(self):
        """Go to previous page"""
        if self.current_page > 1:
            self.current_page -= 1
            self.perform_search(self.current_query, self.current_page)
    
    def next_page(self):
        """Go to next page"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.perform_search(self.current_query, self.current_page)
    
    def go_to_page(self):
        """Go to specific page from input"""
        try:
            page_num = int(self.page_input.text())
            self.go_to_specific_page(page_num)
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Invalid Page", "Please enter a valid page number")
    
    def build_results_html(self, results, query, count, page, total_results, total_pages, results_per_page=50):
        """Build HTML for results with pagination"""
        # Calculate result range for display
        start_num = (page - 1) * results_per_page + 1
        end_num = min(start_num + count - 1, total_results)
        
        html = f"""
        <html>
        <head>
        <style>
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                margin: 0;
                padding: 15px;
                color: #202124;
                background-color: white;
            }}
            .header {{
                margin-bottom: 25px;
                padding-bottom: 15px;
                border-bottom: 2px solid #e8eaed;
            }}
            .query {{
                font-size: 22px;
                color: #202124;
                margin-bottom: 8px;
            }}
            .query-term {{
                color: #d93025;
                font-weight: bold;
            }}
            .stats {{
                font-size: 14px;
                color: #5f6368;
                margin-bottom: 5px;
            }}
            .pagination-info {{
                font-size: 14px;
                color: #5f6368;
                margin-bottom: 15px;
                padding: 10px;
                background-color: #f8f9fa;
                border-radius: 8px;
                border-left: 4px solid #4285f4;
            }}
            .result {{
                margin-bottom: 25px;
                padding: 20px;
                border: 1px solid #e8eaed;
                border-radius: 10px;
                background-color: #f8f9fa;
                transition: all 0.2s;
            }}
            .result:hover {{
                border-color: #4285f4;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                background-color: white;
            }}
            .result-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 12px;
            }}
            .rank {{
                width: 30px;
                height: 30px;
                background: linear-gradient(135deg, #4285f4, #34a853);
                color: white;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
                font-size: 14px;
                flex-shrink: 0;
            }}
            .filename {{
                font-size: 18px;
                color: #1a0dab;
                font-weight: 600;
                flex-grow: 1;
                margin-left: 15px;
            }}
            .score {{
                background-color: #e6f4ea;
                color: #0d652d;
                padding: 5px 12px;
                border-radius: 15px;
                font-size: 13px;
                font-weight: 600;
                flex-shrink: 0;
            }}
            .metadata {{
                font-size: 13px;
                color: #5f6368;
                margin-bottom: 12px;
                padding-left: 45px;
            }}
            .snippet {{
                font-size: 14px;
                color: #3c4043;
                line-height: 1.6;
                padding: 15px;
                background-color: white;
                border-radius: 8px;
                border-left: 4px solid #4285f4;
            }}
            .no-results {{
                text-align: center;
                padding: 60px 20px;
                color: #5f6368;
                font-size: 16px;
            }}
            .trie-note {{
                background-color: #e8f0fe;
                padding: 12px;
                border-radius: 8px;
                margin-bottom: 20px;
                border-left: 4px solid #34a853;
                font-size: 14px;
                color: #3c4043;
            }}
            .history-note {{
                background-color: #fff8e1;
                padding: 12px;
                border-radius: 8px;
                margin-bottom: 20px;
                border-left: 4px solid #f9ab00;
                font-size: 14px;
                color: #3c4043;
            }}
        </style>
        </head>
        <body>
        <div class="header">
            <div class="query">Results for: <span class="query-term">"{query}"</span></div>
            <div class="stats">{count} documents found on this page • {self.current_mode.capitalize()} search</div>
        </div>
        
        <div class="pagination-info">
            <strong>📄 Page {page} of {total_pages}:</strong> Showing results {start_num}-{end_num} of {total_results} total results
        </div>
        """
        
        if self.current_mode == "prefix":
            html += """
            <div class="trie-note">
                <strong>🌳 Trie Prefix Search:</strong> Your prefix was expanded by the Trie data structure 
                to include all matching words before searching.
            </div>
            """
        
        # Add history note if this is a repeated search
        history_count = 0
        for item in self.search_history.get_all():
            if item['query'].lower() == query.lower():
                history_count += 1
        
        if history_count > 1:
            html += f"""
            <div class="history-note">
                <strong>📜 Search History:</strong> You've searched for "{query}" {history_count} times.
                View all searches in History.
            </div>
            """
        
        if not results:
            html += """
            <div class="no-results">
                <div style="font-size: 20px; font-weight: 600; margin-bottom: 15px; color: #5f6368;">
                    No results found on this page
                </div>
                <div style="font-size: 14px; color: #70757a;">
                    Try:
                    <ul style="text-align: left; display: inline-block; margin-top: 15px;">
                        <li>Different search terms</li>
                        <li>Using prefix search mode</li>
                        <li>Checking Trie suggestions on the left</li>
                        <li>Navigating to other pages</li>
                    </ul>
                </div>
            </div>
            """
        else:
            for i, item in enumerate(results, 1):
                filename = item.get("filename", f"Document {start_num + i - 1}")
                score = item.get("score", 0)
                snippet = item.get("snippet", "No snippet available")
                snippet = snippet.replace('\n', ' ')
                
                # Format score
                try:
                    score_value = float(score)
                    score_formatted = f"{score_value:.6f}"
                    if score_value > 0.01:
                        score_color = "#0d652d"
                        score_bg = "#e6f4ea"
                    elif score_value > 0.001:
                        score_color = "#f9ab00"
                        score_bg = "#fff8e1"
                    else:
                        score_color = "#5f6368"
                        score_bg = "#f1f3f4"
                except:
                    score_formatted = str(score)
                    score_color = "#5f6368"
                    score_bg = "#f1f3f4"
                
                rank_num = start_num + i - 1
                
                html += f"""
                <div class="result">
                    <div class="result-header">
                        <div class="rank">{rank_num}</div>
                        <div class="filename">{filename}</div>
                        <div class="score" style="background-color: {score_bg}; color: {score_color}">
                            Score: {score_formatted}
                        </div>
                    </div>
                    <div class="metadata">
                        Occurrences: {item.get('totalOccurrences', 0)} • 
                        Title Match: {'✓ Yes (×2.0 bonus)' if item.get('inTitle', False) else '✗ No'}
                    </div>
                    <div class="snippet">{snippet}</div>
                </div>
                """
        
        html += "</body></html>"
        return html
    
    def show_history(self):
        """Show search history dialog"""
        history = self.search_history.get_all()
        
        if not history:
            QtWidgets.QMessageBox.information(self, "Search History", "No search history yet!")
            return
        
        # Create history dialog
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("📜 Search History")
        dialog.setGeometry(200, 200, 500, 400)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        
        # Header
        header = QtWidgets.QLabel(f"📜 Recent Searches (Last {MAX_HISTORY})")
        header.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #1a73e8;
            padding: 10px;
            border-bottom: 2px solid #e8eaed;
        """)
        layout.addWidget(header)
        
        # History list
        history_list = QtWidgets.QListWidget()
        history_list.setStyleSheet("""
            QListWidget {
                font-size: 14px;
                border: 2px solid #e8f0fe;
                border-radius: 10px;
                background-color: white;
            }
            QListWidget::item {
                padding: 12px;
                border-bottom: 1px solid #f1f3f4;
            }
            QListWidget::item:hover {
                background-color: #e8f0fe;
            }
            QListWidget::item:selected {
                background-color: #1a73e8;
                color: white;
                font-weight: bold;
            }
        """)
        
        for i, entry in enumerate(history, 1):
            item_text = f"{i}. {entry['query']} ({entry['time_str']})"
            item = QtWidgets.QListWidgetItem(item_text)
            item.setData(QtCore.Qt.UserRole, entry['query'])  # Store query for retrieval
            history_list.addItem(item)
        
        layout.addWidget(history_list, 1)
        
        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        
        # Use button
        use_button = QtWidgets.QPushButton("🔍 Use This Search")
        use_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                padding: 10px 20px;
                background-color: #4285f4;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3367d6;
            }
        """)
        
        def use_selected_search():
            current_item = history_list.currentItem()
            if current_item:
                query = current_item.data(QtCore.Qt.UserRole)
                dialog.accept()
                self.search_input.setText(query)
                self.do_search()
        
        use_button.clicked.connect(use_selected_search)
        button_layout.addWidget(use_button)
        
        # Clear button
        clear_button = QtWidgets.QPushButton("🗑️ Clear History")
        clear_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                padding: 10px 20px;
                background-color: #fce8e6;
                color: #d93025;
                border: 1px solid #fad2cf;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #f9c9c5;
            }
        """)
        
        def clear_and_close():
            reply = QtWidgets.QMessageBox.question(
                dialog, "Clear History", 
                "Are you sure you want to clear all search history?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )
            if reply == QtWidgets.QMessageBox.Yes:
                self.search_history.clear()
                dialog.accept()
                QtWidgets.QMessageBox.information(self, "History Cleared", "Search history has been cleared!")
        
        clear_button.clicked.connect(clear_and_close)
        button_layout.addWidget(clear_button)
        
        # Close button
        close_button = QtWidgets.QPushButton("Close")
        close_button.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                padding: 10px 20px;
                background-color: #f1f3f4;
                color: #5f6368;
                border: 1px solid #dadce0;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #e8eaed;
            }
        """)
        close_button.clicked.connect(dialog.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
        # Connect double-click to use search
        history_list.itemDoubleClicked.connect(lambda item: use_selected_search())
        
        dialog.exec_()
    
    def clear_history(self):
        """Clear search history with confirmation"""
        if self.search_history.is_empty():
            QtWidgets.QMessageBox.information(self, "Clear History", "Search history is already empty!")
            return
        
        reply = QtWidgets.QMessageBox.question(
            self, "Clear History", 
            "Are you sure you want to clear all search history?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            self.search_history.clear()
            QtWidgets.QMessageBox.information(self, "History Cleared", "Search history has been cleared!")
            self.status_label.setText("Search history cleared")

def main():
    app = QtWidgets.QApplication(sys.argv)
    
    # Create and show main window
    window = MiniGoogleGUI()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()