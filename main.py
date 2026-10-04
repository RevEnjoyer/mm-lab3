"""
Главное окно приложения асинхронной загрузки файла.

Лабораторная работа 2.2, вариант 1.
Кнопка "Загрузить файл" открывает диалог выбора файла, затем файл
читается в фоновом потоке (WorkerThread) с отображением прогресса,
а интерфейс всё это время остаётся отзывчивым.
"""

import sys

from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from worker_thread import WorkerThread


class MainWindow(QMainWindow):
    """Главное окно приложения."""

    def __init__(self):
        super().__init__()

        self.setWindowTitle('Асинхронная загрузка файла')
        self.setGeometry(100, 100, 420, 180)

        # Ссылку на поток храним как атрибут объекта (self.worker),
        # а не как локальную переменную внутри start_task(). Если бы
        # объект потока жил только как локальная переменная, сборщик
        # мусора Python мог бы уничтожить его сразу после выхода из
        # функции start_task(), не дождавшись завершения run() -
        # поток просто оборвался бы без предупреждения.
        self.worker = None

        self.init_ui()

    def init_ui(self):
        """Создаёт виджеты, раскладку и подключает сигналы к слотам."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        self.load_button = QPushButton('Загрузить файл')

        # QProgressBar - готовый виджет Qt для отображения прогресса.
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.status_label = QLabel('Готово к работе')

        self.load_button.clicked.connect(self.start_task)

        layout = QVBoxLayout()
        layout.addWidget(self.load_button)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
        central_widget.setLayout(layout)

    def start_task(self):
        """Открывает диалог выбора файла и запускает фоновую загрузку."""
        # QFileDialog.getOpenFileName - стандартный системный диалог.
        # Возвращает кортеж (путь, использованный_фильтр). Если
        # пользователь нажал "Отмена", путь будет пустой строкой -
        # это штатная ситуация, а не ошибка, поэтому просто выходим.
        file_path, _ = QFileDialog.getOpenFileName(
            self, 'Выбрать файл для загрузки', '', 'Все файлы (*)'
        )
        if not file_path:
            self.status_label.setText('Загрузка отменена пользователем')
            return

        # Блокируем кнопку на время загрузки - без этого пользователь
        # мог бы нажать "Загрузить файл" повторно ещё до завершения
        # первой загрузки и запустить два потока одновременно, которые
        # начали бы независимо писать в одни и те же виджеты (progress
        # bar, статус) - это и есть гонка состояний (race condition).
        self.load_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText('Загрузка...')

        # Создаём поток для конкретного выбранного файла.
        self.worker = WorkerThread(file_path)

        # Подключаем все три сигнала потока к своим обработчикам
        # В ОСНОВНОМ потоке - именно так данные безопасно "пересекают
        # границу" между фоновым и основным потоком.
        self.worker.progress.connect(self.on_progress)
        self.worker.result_ready.connect(self.on_result)
        self.worker.error_occurred.connect(self.on_error)

        # .start() запускает run() в НОВОМ потоке и сразу возвращает
        # управление - в отличие от прямого вызова self.worker.run(),
        # который выполнил бы всю загрузку синхронно в текущем потоке
        # и заблокировал бы GUI ровно так, как мы пытаемся избежать.
        self.worker.start()

    def on_progress(self, value):
        """Слот: обновляет прогресс-бар (сигнал progress потока)."""
        self.progress_bar.setValue(value)

    def on_result(self, file_name, size_bytes):
        """Слот: обрабатывает успешное завершение загрузки."""
        size_kb = round(size_bytes / 1024, 1)
        self.status_label.setText(f'Готово: {file_name} ({size_kb} КБ)')
        # Разблокируем кнопку - можно загружать следующий файл.
        self.load_button.setEnabled(True)

    def on_error(self, message):
        """Слот: обрабатывает ошибку, возникшую в фоновом потоке."""
        self.status_label.setText(f'Ошибка: {message}')
        self.load_button.setEnabled(True)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
