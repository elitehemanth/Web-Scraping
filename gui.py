"""
gui.py - Smart Web Scraper GUI with threaded LLM analysis and settings.

Features:
- Scraper thread (ScraperThread)
- Analysis thread (AnalysisThread) that calls functions from ai_utils (LLM-backed)
- Settings tab: font size, wrap toggle, dark mode
- AI analysis output rendered as HTML:
    - File name highlighted in red
    - First/top keyword highlighted in green
- Indeterminate progress bar while analysis runs
"""

import threading
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QMainWindow, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QTextEdit, QTabWidget, QProgressBar,
    QFileDialog, QSpinBox, QMessageBox, QHeaderView, QTableWidget,
    QTableWidgetItem, QCheckBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QTextCursor, QFont, QPalette, QColor

import scraper      # your scraper logic
import utils        # your utility functions
import ai_utils     # your AI analysis (LLM-backed summarizer)


class QTextEditLogger(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)

    def write(self, message: str):
        self.moveCursor(QTextCursor.End)
        self.insertPlainText(message)
        self.moveCursor(QTextCursor.End)

    def flush(self):
        pass


class ScraperThread(QThread):
    log_signal = pyqtSignal(str)
    done_signal = pyqtSignal(int)

    def __init__(self, url, keywords, depth):
        super().__init__()
        self.url = url
        self.keywords = keywords
        self.depth = depth
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        try:
            # Only scrape ONE url; depth/keywords not used for now.
            result = scraper.run_scraper(
                self.url,
                keywords=self.keywords,
                depth=self.depth,
                log_signal=self.log_signal
            )
            self.done_signal.emit(1 if result else 0)
        except Exception as e:
            self.log_signal.emit(f"[ERROR] {e}\n")
            self.done_signal.emit(0)


# -----------------------
# Worker thread for AI analysis (non-blocking)
# -----------------------
class AnalysisThread(QThread):
    # Signals to communicate back to GUI
    result_signal = pyqtSignal(str)        # emits HTML result
    error_signal = pyqtSignal(str)         # error message
    finished_signal = pyqtSignal()         # finished (successful or not)

    def __init__(self, file_path, min_length=60, max_length=200, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.min_length = min_length
        self.max_length = max_length
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        try:
            if not os.path.isfile(self.file_path):
                self.error_signal.emit("Selected file does not exist.")
                self.finished_signal.emit()
                return

            # Read file (quick, done off main thread)
            with open(self.file_path, "r", encoding="utf-8") as f:
                text = f.read()

            if not text.strip():
                self.error_signal.emit("File is empty.")
                self.finished_signal.emit()
                return

            # Call ai_utils functions (these may be network/LLM calls)
            try:
                sentiment = ai_utils.sentiment_details(text)
            except Exception as e:
                # If sentiment fails, continue but note the error
                sentiment = f"Sentiment error: {e}"

            try:
                summary = ai_utils.advanced_ai_summary(
                    text, min_length=self.min_length, max_length=self.max_length
                )
            except Exception as e:
                self.error_signal.emit(f"Summary generation failed: {e}")
                self.finished_signal.emit()
                return

            try:
                keywords = ai_utils.keyword_density(text, top_n=5)
            except Exception:
                keywords = []

            # Prepare HTML-formatted result
            file_name = os.path.basename(self.file_path)
            top_keyword = keywords[0] if keywords else None

            # Protect against None summary
            if summary is None:
                summary = ""

            # Highlight first occurrence of top_keyword in the summary (green)
            if top_keyword:
                # Only replace the first plain-text occurrence.
                # Use a simple approach — if summary contains the keyword as-is, replace first match.
                try:
                    # naive replace (case-sensitive); try case-insensitive fallback
                    if top_keyword in summary:
                        summary_html = summary.replace(top_keyword,
                                                       f'<span style="color:green; font-weight:bold;">{top_keyword}</span>',
                                                       1)
                    else:
                        # case-insensitive replacement: find index
                        import re
                        pattern = re.compile(re.escape(top_keyword), re.IGNORECASE)
                        summary_html = pattern.sub(
                            lambda m: f'<span style="color:green; font-weight:bold;">{m.group(0)}</span>',
                            summary,
                            count=1
                        )
                except Exception:
                    summary_html = summary  # fallback
            else:
                summary_html = summary

            # File name in red
            file_html = f'<span style="color:red; font-weight:bold;">{file_name}</span>'

            # Build keywords list HTML
            if keywords:
                keywords_html = ", ".join(
                    f'<span style="font-weight:bold;">{k}</span>' for k in keywords
                )
            else:
                keywords_html = "None"

            result_html = f"""
            <div>
                <div><b>File:</b> {file_html}</div>
                <div style="margin-top:8px;"><b>Sentiment:</b> {sentiment}</div>
                <div style="margin-top:12px;"><b>Summary:</b><br>{summary_html}</div>
                <div style="margin-top:12px;"><b>Top Keywords:</b> {keywords_html}</div>
            </div>
            """

            # Emit the HTML result
            self.result_signal.emit(result_html)

        except Exception as e:
            self.error_signal.emit(f"Unexpected error during analysis: {e}")
        finally:
            self.finished_signal.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Web Scraper")
        self.setMinimumSize(900, 600)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Create tabs
        self.dashboard_tab = QWidget()
        self.settings_tab = QWidget()
        self.logs_tab = QWidget()
        self.database_tab = QWidget()
        self.keyword_tab = QWidget()
        self.ai_tab = QWidget()

        self.tabs.addTab(self.dashboard_tab, "Dashboard")
        self.tabs.addTab(self.settings_tab, "Settings")
        self.tabs.addTab(self.logs_tab, "Logs")
        self.tabs.addTab(self.database_tab, "TXT Files")
        self.tabs.addTab(self.keyword_tab, "Keyword Search")
        self.tabs.addTab(self.ai_tab, "AI Summary")

        self.init_dashboard_tab()
        self.init_settings_tab()
        self.init_logs_tab()
        self.init_database_tab()
        self.init_keyword_tab()
        self.init_ai_tab()

        # Threads
        self.thread = None
        self.analysis_thread = None

        # Apply initial font settings to widgets we'll manage
        self.apply_font_settings()
        self.apply_wrap_settings()

    # Dashboard Tab
    def init_dashboard_tab(self):
        layout = QVBoxLayout()
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("Start URL:"))
        self.url_input = QLineEdit()
        url_layout.addWidget(self.url_input)

        keyword_layout = QHBoxLayout()
        keyword_layout.addWidget(QLabel("Keywords (comma separated):"))
        self.keyword_input = QLineEdit()
        keyword_layout.addWidget(self.keyword_input)

        depth_layout = QHBoxLayout()
        depth_layout.addWidget(QLabel("Crawl Depth:"))
        self.depth_spin = QSpinBox()
        self.depth_spin.setRange(1, 5)
        self.depth_spin.setValue(1)
        depth_layout.addWidget(self.depth_spin)

        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Scraping")
        self.stop_button = QPushButton("Stop Scraping")
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.dashboard_log = QTextEditLogger()

        layout.addLayout(url_layout)
        layout.addLayout(keyword_layout)
        layout.addLayout(depth_layout)
        layout.addLayout(button_layout)
        layout.addWidget(self.progress_bar)
        layout.addWidget(QLabel("Progress Log:"))
        layout.addWidget(self.dashboard_log)
        self.dashboard_tab.setLayout(layout)

        self.start_button.clicked.connect(self.start_scraper)
        self.stop_button.clicked.connect(self.stop_scraper)

    def start_scraper(self):
        url = self.url_input.text().strip()
        keywords = self.keyword_input.text().split(",") if self.keyword_input.text().strip() else []
        depth = self.depth_spin.value()

        if not url:
            QMessageBox.warning(self, "Warning", "Please enter a URL to scrape.")
            return

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.dashboard_log.clear()
        self.thread = ScraperThread(url, keywords, depth)
        self.thread.log_signal.connect(self.dashboard_log.write)
        self.thread.done_signal.connect(self.on_scraper_done)
        self.thread.start()

    def stop_scraper(self):
        if self.thread and self.thread.isRunning():
            self.thread.stop()
        self.dashboard_log.write("\nScraper stopped.\n")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def on_scraper_done(self, count):
        self.dashboard_log.write(f"\nDone. Scraped {count} file(s).\n")
        self.progress_bar.setValue(100)
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.refresh_txt_file_table()
        self.refresh_file_selector_if_needed()

    # Settings Tab (font size, wrap toggle, dark mode)
    def init_settings_tab(self):
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Font Size:"))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 40)
        self.font_size_spin.setValue(12)
        layout.addWidget(self.font_size_spin)

        self.wrap_toggle = QCheckBox("Wrap Text")
        self.wrap_toggle.setChecked(True)
        layout.addWidget(self.wrap_toggle)

        self.dark_mode_toggle = QCheckBox("Dark Mode")
        layout.addWidget(self.dark_mode_toggle)

        layout.addStretch()
        self.settings_tab.setLayout(layout)

        # Connect signals
        self.font_size_spin.valueChanged.connect(self.apply_font_settings)
        self.wrap_toggle.stateChanged.connect(self.apply_wrap_settings)
        self.dark_mode_toggle.stateChanged.connect(self.apply_dark_mode)

    # Apply font settings to interested widgets
    def apply_font_settings(self):
        size = getattr(self, "font_size_spin", None)
        pts = 12
        if size:
            pts = self.font_size_spin.value()
        font = QFont()
        font.setPointSize(pts)

        widgets = [
            getattr(self, "dashboard_log", None),
            getattr(self, "logs_text", None),
            getattr(self, "keyword_search_output", None),
            getattr(self, "ai_summary_output", None)
        ]

        for w in widgets:
            if w:
                w.setFont(font)

    # Apply wrap/no-wrap to text widgets
    def apply_wrap_settings(self):
        wrap_checked = getattr(self, "wrap_toggle", None)
        mode = QTextEdit.WidgetWidth if (wrap_checked and self.wrap_toggle.isChecked()) else QTextEdit.NoWrap

        widgets = [
            getattr(self, "dashboard_log", None),
            getattr(self, "logs_text", None),
            getattr(self, "keyword_search_output", None),
            getattr(self, "ai_summary_output", None)
        ]

        for w in widgets:
            if w:
                w.setLineWrapMode(mode)

    # Simple dark mode using palette adjustments
    def apply_dark_mode(self):
        dm = getattr(self, "dark_mode_toggle", None)
        if not dm:
            return

        if self.dark_mode_toggle.isChecked():
            p = QPalette()
            p.setColor(QPalette.Window, QColor("#121212"))
            p.setColor(QPalette.WindowText, QColor("#ffffff"))
            p.setColor(QPalette.Base, QColor("#1e1e1e"))
            p.setColor(QPalette.Text, QColor("#e6e6e6"))
            p.setColor(QPalette.Button, QColor("#2b2b2b"))
            p.setColor(QPalette.ButtonText, QColor("#ffffff"))
            self.setPalette(p)
        else:
            # Reset to system/default palette
            self.setPalette(QApplication.instance().palette())

    # Logs Tab
    def init_logs_tab(self):
        layout = QVBoxLayout()
        self.logs_text = QTextEditLogger()
        layout.addWidget(QLabel("Application Log:"))
        layout.addWidget(self.logs_text)
        self.logs_tab.setLayout(layout)

    # TXT Files Tab (shows all files in scraped_txt folder)
    def init_database_tab(self):
        layout = QVBoxLayout()
        self.txt_file_table = QTableWidget()
        self.txt_file_table.setColumnCount(2)
        self.txt_file_table.setHorizontalHeaderLabels(["File Name", "Sentiment"])
        self.txt_file_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(QLabel("Scraped TXT files:"))
        layout.addWidget(self.txt_file_table)
        self.database_tab.setLayout(layout)
        self.refresh_txt_file_table()

    def refresh_txt_file_table(self):
        folder = utils.SAVE_DIR
        files = os.listdir(folder) if os.path.exists(folder) else []
        self.txt_file_table.setRowCount(len(files))
        for i, fname in enumerate(files):
            path = os.path.join(folder, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    text = f.read()
                sentiment = ai_utils.sentiment_weight(text)
            except Exception:
                sentiment = 'N/A'
            self.txt_file_table.setItem(i, 0, QTableWidgetItem(fname))
            self.txt_file_table.setItem(i, 1, QTableWidgetItem(str(sentiment)))

    # Keyword Search Tab
    def init_keyword_tab(self):
        layout = QVBoxLayout()
        self.keyword_search_input = QLineEdit()
        self.keyword_search_button = QPushButton("Search in TXT Files")
        self.keyword_search_output = QTextEdit()
        self.keyword_search_output.setReadOnly(True)
        layout.addWidget(QLabel("Keyword:"))
        layout.addWidget(self.keyword_search_input)
        layout.addWidget(self.keyword_search_button)
        layout.addWidget(QLabel("Results:"))
        layout.addWidget(self.keyword_search_output)
        self.keyword_tab.setLayout(layout)
        self.keyword_search_button.clicked.connect(self.run_keyword_search)

    def run_keyword_search(self):
        keyword = self.keyword_search_input.text().strip()
        folder = utils.SAVE_DIR
        results = []
        if not keyword:
            self.keyword_search_output.setText("Enter a keyword.")
            return
        files = os.listdir(folder) if os.path.exists(folder) else []
        for fname in files:
            path = os.path.join(folder, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    text = f.read()
                if keyword.lower() in text.lower():
                    results.append(f"{fname}: FOUND")
            except Exception:
                continue
        if results:
            self.keyword_search_output.setText("\n".join(results))
        else:
            self.keyword_search_output.setText("No matches found.")

    # AI Summary Tab: select and analyze a TXT file
    def init_ai_tab(self):
        layout = QVBoxLayout()
        self.selected_file_path = QLineEdit()
        self.selected_file_path.setReadOnly(True)
        self.browse_file_button = QPushButton("Browse TXT File")
        self.browse_file_button.clicked.connect(self.browse_txt_file)

        self.analyze_file_button = QPushButton("Analyze Selected TXT File")
        self.analyze_file_button.clicked.connect(self.analyze_selected_file)

        self.ai_summary_output = QTextEdit()
        self.ai_summary_output.setReadOnly(True)

        # Busy indicator for analysis (indeterminate progress)
        self.ai_progress = QProgressBar()
        self.ai_progress.setVisible(False)
        # set indeterminate mode by setting range 0..0
        self.ai_progress.setRange(0, 0)

        file_layout = QHBoxLayout()
        file_layout.addWidget(self.selected_file_path)
        file_layout.addWidget(self.browse_file_button)

        layout.addWidget(QLabel("Choose a TXT file:"))
        layout.addLayout(file_layout)
        layout.addWidget(self.analyze_file_button)
        layout.addWidget(self.ai_progress)
        layout.addWidget(QLabel("AI Analysis:"))
        layout.addWidget(self.ai_summary_output)
        self.ai_tab.setLayout(layout)

    def browse_txt_file(self):
        folder = utils.SAVE_DIR
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select TXT file", folder, "Text Files (*.txt)"
        )
        if file_path:
            self.selected_file_path.setText(file_path)

    def analyze_selected_file(self):
        file_path = self.selected_file_path.text()
        if not file_path or not os.path.isfile(file_path):
            self.ai_summary_output.setText("Select a valid TXT file first.")
            return

        # Disable UI controls while running
        self.analyze_file_button.setEnabled(False)
        self.browse_file_button.setEnabled(False)
        self.ai_summary_output.clear()
        self.ai_progress.setVisible(True)

        # Create and start the analysis thread
        self.analysis_thread = AnalysisThread(file_path, min_length=60, max_length=200)
        self.analysis_thread.result_signal.connect(self.handle_analysis_result)
        self.analysis_thread.error_signal.connect(self.handle_analysis_error)
        self.analysis_thread.finished_signal.connect(self.handle_analysis_finished)
        self.analysis_thread.start()

    def handle_analysis_result(self, result_html):
        # This is called in the main thread via signal; render HTML
        self.ai_summary_output.setHtml(result_html)

    def handle_analysis_error(self, error_msg):
        # Append error info to output and also show a popup
        current = self.ai_summary_output.toHtml()
        new_html = current + f"<p style='color:darkorange;'><b>ERROR:</b> {error_msg}</p>"
        self.ai_summary_output.setHtml(new_html)
        QMessageBox.warning(self, "Analysis Error", error_msg)

    def handle_analysis_finished(self):
        # Re-enable controls, hide progress
        self.analyze_file_button.setEnabled(True)
        self.browse_file_button.setEnabled(True)
        self.ai_progress.setVisible(False)
        # Make sure thread object cleaned up
        if self.analysis_thread and self.analysis_thread.isFinished():
            self.analysis_thread = None

    # Optionally refresh file selector after scraping
    def refresh_file_selector_if_needed(self):
        # If adding/supporting a QComboBox selector, refresh here.
        pass


# End of gui.py
