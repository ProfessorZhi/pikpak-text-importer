import sys
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .importer import (
    AppConfig,
    DEFAULT_SESSION_FILE,
    browse_folder,
    extract_share_entries,
    import_text,
    load_app_config,
    save_app_config,
    validate_account,
)
from .paths import resource_root


ASSETS_DIR = resource_root() / "assets"
ICON_PATH = ASSETS_DIR / "pikpak_importer_icon.svg"


class ImportWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)
    progress = Signal(int, int, str)

    def __init__(
        self,
        *,
        text: str,
        username: str | None,
        password: str | None,
        folder_path: str,
        session_file: str,
    ) -> None:
        super().__init__()
        self.text = text
        self.username = username
        self.password = password
        self.folder_path = folder_path
        self.session_file = session_file

    def run(self) -> None:
        try:
            import asyncio

            entries, results = asyncio.run(
                import_text(
                    text=self.text,
                    username=self.username,
                    password=self.password,
                    folder_path=self.folder_path,
                    session_file=self.session_file,
                    progress_callback=lambda current, total, message: self.progress.emit(
                        current,
                        total,
                        message,
                    ),
                )
            )
            self.finished.emit({"entries": entries, "results": results})
        except Exception as exc:
            self.failed.emit(str(exc))


class ValidateWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, *, username: str | None, password: str | None, session_file: str) -> None:
        super().__init__()
        self.username = username
        self.password = password
        self.session_file = session_file

    def run(self) -> None:
        try:
            import asyncio

            result = asyncio.run(
                validate_account(
                    username=self.username,
                    password=self.password,
                    session_file=self.session_file,
                )
            )
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class FolderBrowseWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        *,
        username: str | None,
        password: str | None,
        session_file: str,
        parent_id: str | None,
        parent_path: str,
    ) -> None:
        super().__init__()
        self.username = username
        self.password = password
        self.session_file = session_file
        self.parent_id = parent_id
        self.parent_path = parent_path

    def run(self) -> None:
        try:
            import asyncio

            result = asyncio.run(
                browse_folder(
                    username=self.username,
                    password=self.password,
                    session_file=self.session_file,
                    parent_id=self.parent_id,
                    parent_path=self.parent_path,
                )
            )
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PikPak 文本批量转存")
        self.resize(1080, 840)
        self.account_validated = False
        self.current_folder_id: str | None = None
        self.current_folder_path = "/"
        self.folder_stack: list[tuple[str | None, str]] = []
        self.worker_thread: QThread | None = None
        self.worker: QObject | None = None
        self.pending_action = ""

        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(10)

        self.status_label = QLabel("请先填写账号信息，保存并校验。")
        self.status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        root.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        root.addWidget(self.progress_bar)

        form = QFormLayout()
        root.addLayout(form)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("邮箱 / 用户名 / 手机号")
        form.addRow("账号", self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("首次登录或会话失效时需要")
        form.addRow("密码", self.password_input)

        self.current_folder_label = QLabel("/")
        self.current_folder_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        form.addRow("当前目录", self.current_folder_label)

        self.folder_combo = QComboBox()
        self.folder_combo.setEnabled(False)
        form.addRow("下一层文件夹", self.folder_combo)

        session_row = QHBoxLayout()
        self.session_input = QLineEdit(str(DEFAULT_SESSION_FILE))
        self.session_input.setPlaceholderText("选择会话缓存文件位置")
        session_row.addWidget(self.session_input)
        self.session_browse_button = QPushButton("选择位置")
        self.session_browse_button.clicked.connect(self.choose_session_file)
        session_row.addWidget(self.session_browse_button)
        form.addRow("会话存储", session_row)

        config_row = QHBoxLayout()
        root.addLayout(config_row)

        self.save_config_button = QPushButton("保存配置")
        self.save_config_button.clicked.connect(self.save_config_clicked)
        config_row.addWidget(self.save_config_button)

        self.validate_button = QPushButton("校验账号")
        self.validate_button.clicked.connect(self.validate_config_clicked)
        config_row.addWidget(self.validate_button)

        self.load_config_button = QPushButton("重新载入配置")
        self.load_config_button.clicked.connect(self.load_config_into_form)
        config_row.addWidget(self.load_config_button)

        browse_row = QHBoxLayout()
        root.addLayout(browse_row)

        self.up_button = QPushButton("返回上一级")
        self.up_button.clicked.connect(self.go_up_folder)
        browse_row.addWidget(self.up_button)

        self.enter_button = QPushButton("进入所选文件夹")
        self.enter_button.clicked.connect(self.enter_selected_folder)
        browse_row.addWidget(self.enter_button)

        self.reset_root_button = QPushButton("回到根目录")
        self.reset_root_button.clicked.connect(self.go_root_folder)
        browse_row.addWidget(self.reset_root_button)

        action_row = QHBoxLayout()
        root.addLayout(action_row)

        self.open_button = QPushButton("打开文本文件")
        self.open_button.clicked.connect(self.open_text_file)
        action_row.addWidget(self.open_button)

        self.extract_button = QPushButton("预览将创建的文件夹")
        self.extract_button.clicked.connect(self.preview_entries)
        action_row.addWidget(self.extract_button)

        self.import_button = QPushButton("开始转存")
        self.import_button.clicked.connect(self.start_import)
        action_row.addWidget(self.import_button)

        self.input_text = QPlainTextEdit()
        self.input_text.setPlaceholderText("把包含 https://mypikpak.com/s/... 的文本粘贴到这里")
        root.addWidget(self.input_text, 3)

        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        root.addWidget(self.log_text, 2)

        self.load_config_into_form()
        self.set_log(
            "使用说明：\n"
            "1. 填写账号和密码\n"
            "2. 选择会话存储位置\n"
            "3. 点击“保存配置”\n"
            "4. 点击“校验账号”\n"
            "5. 校验成功后，按层浏览目录。当前目录就是最终转存的父目录\n"
            "6. 每个分享链接都会单独形成一个子文件夹，并放到当前目录下面"
        )
        self.update_action_state()

    def current_config(self) -> AppConfig:
        return AppConfig(
            username=self.username_input.text().strip(),
            password=self.password_input.text(),
            folder_path=self.current_folder_path,
            session_file=self.session_input.text().strip() or str(DEFAULT_SESSION_FILE),
        )

    def set_log(self, text: str) -> None:
        self.log_text.setPlainText(text)

    def choose_session_file(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "选择会话文件保存位置",
            self.session_input.text().strip() or str(DEFAULT_SESSION_FILE),
            "JSON Files (*.json);;All Files (*.*)",
        )
        if file_path:
            self.session_input.setText(file_path)

    def load_config_into_form(self) -> None:
        config = load_app_config()
        self.username_input.setText(config.username)
        self.password_input.setText(config.password)
        self.session_input.setText(config.session_file or str(DEFAULT_SESSION_FILE))
        self.current_folder_id = None
        self.current_folder_path = "/"
        self.folder_stack = []
        self.current_folder_label.setText(self.current_folder_path)
        self.folder_combo.clear()
        self.folder_combo.setEnabled(False)
        self.account_validated = False
        self.status_label.setText("配置已载入，请重新校验账号。")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.update_action_state()

    def save_config_clicked(self) -> None:
        username = self.username_input.text().strip()
        if not username:
            QMessageBox.warning(self, "缺少配置", "请先填写账号。")
            return
        save_app_config(self.current_config())
        self.account_validated = False
        self.folder_combo.clear()
        self.folder_combo.setEnabled(False)
        self.status_label.setText("配置已保存，请点击“校验账号”。")
        self.set_log("配置已保存。校验成功后会加载当前目录下一层文件夹。")
        self.update_action_state()

    def validate_config_clicked(self) -> None:
        username = self.username_input.text().strip()
        password = self.password_input.text()
        session_file = self.session_input.text().strip() or str(DEFAULT_SESSION_FILE)
        has_session_file = Path(session_file).exists()
        if not username:
            QMessageBox.warning(self, "缺少配置", "请先填写账号。")
            return
        if not password and not has_session_file:
            QMessageBox.warning(self, "缺少配置", "首次登录或会话失效时，请输入密码。")
            return

        save_app_config(self.current_config())
        self.pending_action = "validate"
        self.start_worker(
            ValidateWorker(username=username, password=password, session_file=session_file),
            "正在校验账号...",
            indeterminate=True,
        )

    def start_worker(self, worker: QObject, status: str, *, indeterminate: bool) -> None:
        self.set_busy(True, status, indeterminate=indeterminate)
        self.worker_thread = QThread(self)
        self.worker = worker
        worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(worker.run)
        if hasattr(worker, "progress"):
            worker.progress.connect(self.on_progress)
        worker.finished.connect(self.on_worker_finished)
        worker.failed.connect(self.on_worker_failed)
        worker.finished.connect(self.worker_thread.quit)
        worker.failed.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.cleanup_worker)
        self.worker_thread.start()

    def cleanup_worker(self) -> None:
        if self.worker_thread is not None:
            self.worker_thread.deleteLater()
        self.worker_thread = None
        self.worker = None

    def on_worker_finished(self, payload: object) -> None:
        action = self.pending_action
        self.pending_action = ""
        if action == "validate":
            self.finish_validate(payload if isinstance(payload, dict) else {})
            return
        if action == "browse":
            self.finish_browse(payload if isinstance(payload, dict) else {})
            return
        if action == "import":
            if not isinstance(payload, dict):
                self.on_worker_failed("导入线程返回的数据格式不正确。")
                return
            entries = payload.get("entries", [])
            results = payload.get("results", [])
            self.finish_import(entries, results)

    def on_worker_failed(self, message: str) -> None:
        action = self.pending_action
        self.pending_action = ""
        if action == "validate":
            self.account_validated = False
            self.folder_combo.clear()
            self.folder_combo.setEnabled(False)
            self.set_busy(False, "账号校验失败。", indeterminate=False)
            self.set_log(f"账号校验失败：{message}")
            QMessageBox.critical(self, "校验失败", message)
            return
        if action == "browse":
            self.set_busy(False, "目录加载失败。", indeterminate=False)
            self.set_log(f"目录加载失败：{message}")
            QMessageBox.critical(self, "目录加载失败", message)
            return
        self.set_busy(False, "执行失败。", indeterminate=False)
        self.progress_bar.setValue(0)
        self.set_log(f"执行失败：{message}")
        QMessageBox.critical(self, "执行失败", message)

    def set_busy(self, busy: bool, message: str, *, indeterminate: bool) -> None:
        self.status_label.setText(message)
        self.save_config_button.setEnabled(not busy)
        self.validate_button.setEnabled(not busy)
        self.load_config_button.setEnabled(not busy)
        self.session_browse_button.setEnabled(not busy)
        self.username_input.setEnabled(not busy)
        self.password_input.setEnabled(not busy)
        self.session_input.setEnabled(not busy)

        if busy:
            if indeterminate:
                self.progress_bar.setRange(0, 0)
            else:
                self.progress_bar.setRange(0, 100)
                self.progress_bar.setValue(0)
            self.folder_combo.setEnabled(False)
            self.up_button.setEnabled(False)
            self.enter_button.setEnabled(False)
            self.reset_root_button.setEnabled(False)
            self.open_button.setEnabled(False)
            self.extract_button.setEnabled(False)
            self.import_button.setEnabled(False)
            self.input_text.setReadOnly(True)
            return

        self.progress_bar.setRange(0, 100)
        self.update_action_state()

    def on_progress(self, current: int, total: int, message: str) -> None:
        safe_total = max(total, 1)
        percentage = int((current / safe_total) * 100)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(max(0, min(100, percentage)))
        self.status_label.setText(message)

    def update_action_state(self) -> None:
        nav_enabled = self.account_validated
        self.folder_combo.setEnabled(nav_enabled and self.folder_combo.count() > 0)
        self.up_button.setEnabled(nav_enabled and self.current_folder_path != "/")
        self.enter_button.setEnabled(nav_enabled and self.folder_combo.count() > 0)
        self.reset_root_button.setEnabled(nav_enabled and self.current_folder_path != "/")
        self.open_button.setEnabled(nav_enabled)
        self.extract_button.setEnabled(nav_enabled)
        self.import_button.setEnabled(nav_enabled)
        self.input_text.setReadOnly(not nav_enabled)
        self.current_folder_label.setText(self.current_folder_path)

    def populate_folder_combo(self, folders: list[dict]) -> None:
        self.folder_combo.clear()
        for item in folders:
            self.folder_combo.addItem(item["name"], item)

    def finish_validate(self, payload: dict) -> None:
        self.account_validated = True
        self.current_folder_id = payload.get("current_id")
        self.current_folder_path = payload.get("current_path", "/")
        self.folder_stack = []
        self.populate_folder_combo(payload.get("folders", []))
        self.set_busy(False, "账号校验通过，请按层选择目标目录。", indeterminate=False)
        self.progress_bar.setValue(100)

        quota = payload.get("quota", {})
        usage = quota.get("usage")
        limit = quota.get("limit")
        if usage is not None and limit is not None:
            self.set_log(
                f"账号校验通过。\n当前容量使用：{usage} / {limit}\n当前目录：{self.current_folder_path}"
            )
        else:
            self.set_log(f"账号校验通过。\n当前目录：{self.current_folder_path}")

        QMessageBox.information(
            self,
            "校验成功",
            "账号可用。请按层浏览目录，当前目录就是最终转存的父目录。",
        )

    def browse_to(self, parent_id: str | None, parent_path: str) -> None:
        self.pending_action = "browse"
        self.start_worker(
            FolderBrowseWorker(
                username=self.username_input.text().strip() or None,
                password=self.password_input.text() or None,
                session_file=self.session_input.text().strip() or str(DEFAULT_SESSION_FILE),
                parent_id=parent_id,
                parent_path=parent_path,
            ),
            "正在加载目录...",
            indeterminate=True,
        )

    def finish_browse(self, payload: dict) -> None:
        self.current_folder_id = payload.get("current_id")
        self.current_folder_path = payload.get("current_path", "/")
        self.populate_folder_combo(payload.get("folders", []))
        save_app_config(self.current_config())
        self.set_busy(False, f"当前目录：{self.current_folder_path}", indeterminate=False)
        self.progress_bar.setValue(100)

    def enter_selected_folder(self) -> None:
        data = self.folder_combo.currentData()
        if not data:
            return
        self.folder_stack.append((self.current_folder_id, self.current_folder_path))
        self.browse_to(parent_id=data.get("id"), parent_path=data.get("path", "/"))

    def go_up_folder(self) -> None:
        if not self.folder_stack:
            return
        parent_id, parent_path = self.folder_stack.pop()
        self.browse_to(parent_id=parent_id, parent_path=parent_path)

    def go_root_folder(self) -> None:
        self.folder_stack = []
        self.browse_to(parent_id=None, parent_path="/")

    def open_text_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择文本文件",
            "",
            "Text Files (*.txt);;All Files (*.*)",
        )
        if not file_path:
            return
        with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
            self.input_text.setPlainText(handle.read())
        self.status_label.setText(f"已载入文件：{file_path}")

    def preview_entries(self) -> None:
        text = self.input_text.toPlainText().strip()
        entries = extract_share_entries(text)
        if not entries:
            self.set_log("没有找到 PikPak 分享链接。")
            return

        lines = [
            f"当前目标父目录：{self.current_folder_path}",
            "",
            f"共识别 {len(entries)} 个链接，将处理为这些子文件夹：",
            "",
        ]
        lines.extend(
            f"{index}. {entry.label} <- {entry.link.url}"
            for index, entry in enumerate(entries, start=1)
        )
        self.set_log("\n".join(lines))

    def start_import(self) -> None:
        if not self.account_validated:
            QMessageBox.warning(self, "未校验", "请先保存配置并校验账号。")
            return

        text = self.input_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "缺少文本", "请先粘贴包含 PikPak 链接的文本。")
            return

        self.pending_action = "import"
        self.start_worker(
            ImportWorker(
                text=text,
                username=self.username_input.text().strip() or None,
                password=self.password_input.text() or None,
                folder_path=self.current_folder_path,
                session_file=self.session_input.text().strip() or str(DEFAULT_SESSION_FILE),
            ),
            "正在转存...",
            indeterminate=False,
        )

    def finish_import(self, entries: list, results: list) -> None:
        self.set_busy(False, "准备就绪", indeterminate=False)
        self.progress_bar.setValue(100)
        success_count = 0
        lines = [
            f"目标父目录：{self.current_folder_path}",
            "",
            f"共处理 {len(entries)} 个链接。",
            "",
        ]
        for index, result in enumerate(results, start=1):
            if result.ok:
                success_count += 1
                lines.append(f"[{index}/{len(results)}] 成功：{result.name}")
            else:
                lines.append(f"[{index}/{len(results)}] 失败：{result.url} | {result.error}")

        lines.append("")
        lines.append(f"完成，成功 {success_count} / {len(results)}")
        self.set_log("\n".join(lines))
        self.status_label.setText(f"完成，成功 {success_count} / {len(results)}")
        QMessageBox.information(self, "处理完成", f"成功 {success_count} / {len(results)}")


def gui_main() -> int:
    app = QApplication(sys.argv)
    if ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(ICON_PATH)))
    window = MainWindow()
    window.show()
    return app.exec()
