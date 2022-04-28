import csv
import sqlite3
import sys
import datetime
import pymorphy2
from PyQt5.QtCore import *
from PyQt5 import uic, QtCore, QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QTableWidgetItem

from design import Ui_MainWindow


class MyWidget(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle('Контроль бюджета')
        self.initUi()

    def initUi(self):
        self.setFixedSize(931, 771)
        self.database = sqlite3.connect('database.db')
        self.add_spending_button_2.clicked.connect(self.addSpending)
        self.update_norm_button_2.clicked.connect(self.updateDayNorm)
        self.updateTableButton.clicked.connect(self.updateTableData)
        self.export_stats_button.clicked.connect(self.exportToCSVFile)
        self.calculate_statistics_button.clicked.connect(self.getStatistic)
        self.clearSpendingButton.clicked.connect(self.clearSpending)
        self.deleteLastSpendingButton.clicked.connect(self.deleteLastSpending)
        self.importFromCSVFileButton.clicked.connect(self.importFromCSVFile)
        self.cancelTableUpdateButton.clicked.connect(self.updateTableData)
        self.saveUpdatesButton.clicked.connect(self.saveTable)
        self.pymorphy_analizer = pymorphy2.MorphAnalyzer()
        self.createTables()
        self.updateStatistics()
        self.updateTableData()

    def database_save_request(self, request):  # запрос на сохранение данных в бд
        self.database.execute(request)
        self.database.commit()

    def createTables(self):
        try:
            self.database_save_request(
                f'CREATE TABLE account_information ('
                f'days_user INTEGER,'
                f'all_spent INTEGER,'
                f'day_norm INTEGER,'
                f'last_request STRING'
                f')'
            )

            self.database_save_request(
                f'CREATE TABLE spending ('
                f'spending_name STRING,'
                f'spending_price INTEGER,'
                f'spending_category STRING,'
                f'spending_date STRING,'
                f'spending_time STRING,'
                f'spending_id INT'
                f')'
            )
            self.database_save_request(
                f'INSERT INTO account_information ('
                f'days_user,'
                f'all_spent,'
                f'day_norm,'
                f'last_request) VALUES ('
                f'0,'
                f'0,'
                f'0,'
                f'"")'
            )

            print('# DATABASE CREATED')
        except sqlite3.OperationalError:
            print('# DATABASE ALREADY CREATED')

    def deleteLastSpending(self):
        last_spending_id = self.database.execute(
            f'SELECT spending_id '
            f'FROM spending'
        ).fetchall()

        if last_spending_id:
            if self.showCritical(
                    critical_title='Удалить последнюю трату?'
            ) == QMessageBox.Yes:
                if last_spending_id:
                    last_spending_id = last_spending_id[-1][0]

                    all_spent = self.database.execute(
                        f'SELECT all_spent '
                        f'FROM account_information'
                    ).fetchone()[0]
                    spent_price = self.database.execute(
                        f'SELECT spending_price '
                        f'FROM spending '
                        f'WHERE spending_id={last_spending_id}'
                    ).fetchone()[0]
                    self.database_save_request(
                        f'UPDATE account_information '
                        f'SET all_spent={all_spent - spent_price}'
                    )
                    self.database_save_request(
                        f'DELETE FROM spending WHERE '
                        f'spending_id={last_spending_id}'
                    )
                    self.updateTableData()
        else:
            self.showError('У вас нет трат.')

    def clearSpending(self):
        database_table = self.database.execute(
            f'SELECT spending_id '
            f'FROM spending'
        ).fetchall()[::-1]
        if database_table:
            if self.showCritical(
                    critical_text='Это сотрёт все ваши траты, и заменит их тратами из файла.\n'
                                  'Предварительно сохраните текущие данные во вкладке "Профиль" -> '
                                  'Экспортировать данные в CSV-файл. Спасибо за понимание.'
            ) == QMessageBox.Yes:

                for row in database_table:
                    self.database_save_request(
                        f'DELETE FROM spending WHERE '
                        f'spending_id={row[0]}'
                    )
                self.database_save_request(
                    f'UPDATE account_information '
                    f'SET all_spent=0'
                )
                self.updateTableData()
                self.updateStatistics()
                return True
            else:
                return False
        else:
            self.showError('У вас нет трат.')
            return True

    def saveTable(self):
        database_table = self.database.execute(
            f'SELECT spending_id '
            f'FROM spending'
        ).fetchall()[::-1]

        if database_table:
            if self.showCritical() == QMessageBox.Yes:

                row_count = self.all_spending_table.rowCount()
                col_count = self.all_spending_table.columnCount()

                for row in range(row_count):
                    spending = []
                    for col in range(col_count):
                        spending.append(
                            self.all_spending_table.item(
                                row, col
                            ).text()
                        )
                    self.database_save_request(
                        f'UPDATE spending SET '
                        f'spending_name="{spending[0]}",'
                        f'spending_price={int(spending[1])},'
                        f'spending_category="{spending[2]}" '
                        f'WHERE spending_id={spending[5]}'
                    )
        else:
            self.showError('У вас нет трат.')

    def updateTableData(self):
        self.all_spending_table.setColumnCount(6)
        row_count = 1
        self.all_spending_table.setRowCount(row_count)
        database_table = self.database.execute(
            f'SELECT * '
            f'FROM spending'
        ).fetchall()[::-1]

        for row in range(len(database_table)):
            for element in range(len(database_table[row])):
                element_text = str(
                    database_table[row][element]
                )
                element_text = QTableWidgetItem(element_text)
                self.all_spending_table.setItem(row,
                                                element,
                                                element_text)
            row_count += 1
            self.all_spending_table.setRowCount(row_count)

        self.all_spending_table.setRowCount(row_count - 1)

        for row in range(len(database_table)):
            for element in range(3, 6):
                self.all_spending_table.item(
                    row, element
                ).setFlags(
                    Qt.ItemIsEditable
                )

    def updateProgressBar(self, day_norm, today):
        try:
            if int(day_norm) < int(today):
                result = 100
            else:
                result = (int(today) / int(day_norm)) * 100
            self.norm_progress.setProperty("value", result)

        except ZeroDivisionError:
            self.norm_progress.setProperty("value", 0)

    def updateDayNorm(self):
        day_norm = self.day_spending_2.text()
        day_norm = int(day_norm)

        if day_norm > 0:
            self.day_spending_2.setText('')
            self.database_save_request(
                f'UPDATE account_information '
                f'SET day_norm={day_norm}'
            )
            self.updateStatistics()
        else:
            self.showError('Введи корректное значение.')

    def updateStatistics(self):

        spending = self.database.execute(
            f'SELECT '
            f'spending_price,'
            f'spending_date '
            f'FROM spending'
            f''
        ).fetchall()
        # day norm
        day_norm = \
            self.database.execute(
                f'SELECT day_norm FROM account_information'
            ).fetchone()

        if day_norm != None:
            day_norm = day_norm[0]
        else:
            day_norm = 0

        self.daily_norm_2.setText('Дневная норма: ' +
                                  str(day_norm) +
                                  'р')

        #   yesterday
        now_date = datetime.datetime.now() - datetime.timedelta(days=1)
        now_date = str(now_date)
        now_date = now_date.split()[0]
        yesterday_spending = 0

        for spend in spending:
            if spend[1] == now_date:
                yesterday_spending += int(spend[0])

        yesterday_spending = str(yesterday_spending)

        self.yesterday_2.setText('Вчера: ' +
                                 yesterday_spending +
                                 'р')

        #   today
        now_date = datetime.datetime.now()
        now_date = str(now_date)
        now_date = now_date.split()[0]
        today_spending = 0

        for spend in spending:
            if spend[1] == now_date:
                today_spending += int(spend[0])

        today_spending = str(today_spending)

        self.today_2.setText('Сегодня: ' +
                             today_spending +
                             'р')

        self.updateProgressBar(day_norm, today_spending)

        #   check day norm
        if int(today_spending) >= int(day_norm) and int(day_norm) > 0:
            self.showError('Осторожно, вы '
                           'превысили допустимый '
                           'дневной лимит.')

        # this week
        this_week_spending = 0

        for i in range(0, 7):
            now_date = datetime.datetime.now() - datetime.timedelta(days=i)
            now_date = str(now_date)
            now_date = now_date.split()[0]
            spending = self.database.execute(
                f'SELECT spending_price '
                f'FROM spending WHERE '
                f'spending_date="{now_date}"'
            ).fetchall()

            for i in spending:
                this_week_spending += i[0]

        self.this_week_2.setText('На этой неделе: ' +
                                 str(this_week_spending) +
                                 'р')

        # this month
        this_month_spending = 0

        for i in range(0, 30):
            now_date = datetime.datetime.now() - datetime.timedelta(days=i)
            now_date = str(now_date)
            now_date = now_date.split()[0]
            spending = self.database.execute(
                f'SELECT spending_price '
                f'FROM spending WHERE '
                f'spending_date="{now_date}"'
            ).fetchall()

            for i in spending:
                this_month_spending += i[0]

        self.this_month_2.setText('В этом меcяце: ' +
                                  str(this_month_spending) +
                                  'р')

        # last week
        this_week_spending = 0

        for i in range(0, 7):
            now_date = datetime.datetime.now() - datetime.timedelta(days=i + 7)
            now_date = str(now_date)
            now_date = now_date.split()[0]
            spending = self.database.execute(
                f'SELECT spending_price '
                f'FROM spending WHERE '
                f'spending_date="{now_date}"'
            ).fetchall()

            for i in spending:
                this_week_spending += i[0]

        self.last_week_2.setText('На прошлой неделе: ' +
                                 str(this_week_spending) +
                                 'р')

        # last month
        last_month_spending = 0

        for i in range(0, 30):

            now_date = datetime.datetime.now() - datetime.timedelta(days=i + 30)
            now_date = str(now_date)
            now_date = now_date.split()[0]

            spending = self.database.execute(
                f'SELECT spending_price '
                f'FROM spending WHERE '
                f'spending_date="{now_date}"'
            ).fetchall()
            for i in spending:
                last_month_spending += i[0]

        self.last_month_2.setText('В прошлом месяце: ' +
                                  str(last_month_spending) +
                                  'р')

        self.updateTableData()

    def addSpending(self):
        try:
            spending_name = str(
                self.spending_name_2.text()
            )
            spending_price = int(
                self.spending_price_2.text()
            )
            if spending_name != '' and spending_price != '':
                if int(spending_price) > 0:
                    spending_category = str(
                        self.spending_category_2.currentText()
                    )
                    self.spending_name_2.setText(
                        ''
                    )
                    self.spending_price_2.setText(
                        ''
                    )

                    save_date = datetime.datetime.now()
                    save_date = str(save_date)
                    save_date = save_date.split()[0]

                    save_time = datetime.datetime.now().time()
                    save_time = str(
                        save_time
                    )
                    save_time = save_time.split(':')[:2]
                    save_time = ':'.join(
                        save_time
                    )

                    all_spent = self.database.execute(
                        f'SELECT all_spent '
                        f'FROM account_information'
                    ).fetchone()

                    if all_spent != None:
                        all_spent = all_spent[0]
                        self.database_save_request(
                            f'UPDATE account_information SET '
                            f'all_spent={all_spent + int(spending_price)}'
                        )

                    else:
                        self.database_save_request(
                            f'UPDATE account_information SET '
                            f'all_spent=0'
                        )

                    last_id = self.database.execute(
                        f'SELECT spending_id FROM spending'
                    ).fetchall()

                    if not last_id:
                        last_id = 1
                    else:

                        last_id = last_id[-1][0] + 1

                    self.database_save_request(
                        f'INSERT INTO spending ('
                        f'spending_name,'
                        f'spending_price,'
                        f'spending_category,'
                        f'spending_date,'
                        f'spending_time,'
                        f'spending_id)'
                        f'VALUES ('
                        f'"{spending_name}",'
                        f'{spending_price},'
                        f'"{spending_category}",'
                        f'"{save_date}",'
                        f'"{save_time}",'
                        f'{last_id});'
                    )
                    self.updateStatistics()

                else:
                    self.showError('Введи корректное значение.')

            else:
                self.showError('Одно из полей на заполнено.')

        except ValueError:
            self.showError('Введите корректное значение.')

        except Exception:
            self.showError('Неизвестная ошибка. Повторите попытку.')

    def importFromCSVFile(self):
        csv_file_path = QtWidgets.QFileDialog.getOpenFileName()[0]
        csv_file_path_length = csv_file_path[
                               len(
                                   csv_file_path
                               ) - 4:len(
                                   csv_file_path
                               )
                               ]
        if self.clearSpending():
            if '.csv' in csv_file_path_length:
                with open(csv_file_path, encoding='UTF-8') as f:
                    reader = csv.reader(f)
                    try:
                        for row in reader:
                            if not 'spending_name' in row and row != []:
                                self.database_save_request(
                                    f'INSERT INTO spending ('
                                    f'spending_name,'
                                    f'spending_price,'
                                    f'spending_category,'
                                    f'spending_date,'
                                    f'spending_time,'
                                    f'spending_id)'
                                    f'VALUES ('
                                    f'"{row[0]}",'
                                    f'{row[1]},'
                                    f'"{row[2]}",'
                                    f'"{row[4]}",'
                                    f'"{row[3]}",'
                                    f'{row[5]});'
                                )
                        self.updateTableData()
                        self.updateStatistics()
                    except IndexError:
                        self.showError('Неверный формат записи CSV-файла. '
                                       'При экспорте приложение "Контроль бюджета" '
                                       'Само создаёт нужный формат CSV-таблицы. '
                                       'Пожалуйста, загружайте только файлы, созданные '
                                       'этим приложением.')
                    except Exception:
                        self.showError('Неизвестная ошибка. Возможно, '
                                       'файл не соответствует '
                                       'стандартам, или повреждёт. \n'
                                       'Убедитесь в работоспособности '
                                       'вашего файла и повторите попытку.')
            else:
                self.showError('Файл не является CSV. Импорт остановлен.')

    def exportToCSVFile(self):
        try:
            filename = self.export_stats_input.text()
            if '.' in filename:
                fields = self.database.execute(
                    f'SELECT spending_name,'
                    f'spending_price,'
                    f'spending_category,'
                    f'spending_time,'
                    f'spending_date,'
                    f'spending_id '
                    f'FROM '
                    f'spending'
                ).fetchall()

                with open(filename, 'w', encoding='UTF-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(
                        ['spending_name',
                         'spending_price',
                         'spending_category',
                         'spending_time',
                         'spending_date',
                         'spending_id']
                    )
                    writer.writerows(fields)
                    self.export_stats_input.setText('')
                    self.showCritical(critical_text=f'Данные экспортированы в файл "{filename}"')
            else:
                self.showError('Укажите название файла с расширением.')
        except FileNotFoundError:
            self.showError('Введите корректное имя файла.')

    def getStatistic(self):
        all_spent = self.database.execute(
            f'SELECT all_spent '
            f'FROM account_information'
        )
        all_spent = all_spent.fetchone()[0]

        using_days = self.database.execute(
            f'SELECT spending_date, '
            f'spending_price '
            f'FROM spending'
        ).fetchall()

        if using_days:
            first_using_date = using_days[0][0].split('-')

            first_using_year = int(
                first_using_date[0]
            )

            first_using_month = int(
                first_using_date[1]
            )

            first_using_day = int(
                first_using_date[2]
            )

            first_using_day = datetime.date(year=first_using_year,
                                            month=first_using_month,
                                            day=first_using_day)

            last_using_date = datetime.datetime.now().date()

            all_using_date = last_using_date - first_using_day
            all_using_date = str(
                all_using_date
            )

            all_using_date = all_using_date.split(maxsplit=1)

            if len(all_using_date) < 2:
                all_using_date = str(
                    1
                )
            else:
                all_using_date = str(
                    all_using_date[0]
                )

            spent_prices = [i[1] for i in using_days]

            max_spent_price = str(
                max(spent_prices)
            )

            min_spent_price = str(
                min(spent_prices)
            )

            middle_spent_price = str(
                round(
                    sum(spent_prices) / len(spent_prices),
                    2)
            )

            price_analizer = self.pymorphy_analizer.parse('рубль')[0]
            day_analizer = self.pymorphy_analizer.parse('день')[0]

            def analize(number, analizer=price_analizer):
                return analizer.make_agree_with_number(round(float(
                    number
                ))).word

            def get_analizers():
                middle_analizer = analize(middle_spent_price)
                middle_analizer = f'Средняя потраченная сумма: ' \
                                  f'{middle_spent_price} ' \
                                  f'{middle_analizer}'

                min_analizer = analize(min_spent_price)
                min_analizer = f'Мин. потраченная сумма: ' \
                               f'{min_spent_price} ' \
                               f'{min_analizer}'

                max_analizer = analize(max_spent_price)
                max_analizer = f'Макс. потраченная сумма: ' \
                               f'{max_spent_price} ' \
                               f'{max_analizer}'

                all_analizer = analize(all_spent)
                all_analizer = f'Всего потрачено за всё время: ' \
                               f'{str(all_spent)} ' \
                               f'{all_analizer}'

                all_using_analizer = analize(all_using_date, day_analizer)
                all_using_analizer = f'Приложение используется: ' \
                                     f'{all_using_date} ' \
                                     f'{all_using_analizer}'

                self.min_sum.setText(min_analizer)
                self.max_sum.setText(max_analizer)
                self.middle_sum.setText(middle_analizer)
                self.app_used.setText(all_using_analizer)
                self.all_spent.setText(all_analizer)

            get_analizers()
        else:
            self.showError('Вы ещё не использовали приложение')

    def showError(self, error_msg):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText("Неполадки 🤔")
        msg.setInformativeText(error_msg)
        msg.setWindowTitle("Ошибка")
        msg.exec_()

    def showCritical(self, critical_title='Предупреждение',
                     critical_text='Вы уверены?'):
        msgBox = QMessageBox()
        msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msgBox.setText(critical_text)
        msgBox.setWindowTitle(critical_title)
        msgBox.setIcon(QMessageBox.Warning)
        result = msgBox.exec_()
        return result


def exception_hook(exctype, value, traceback):
    traceback_formated = traceback.format_exception(exctype, value, traceback)
    traceback_string = "".join(traceback_formated)
    print(traceback_string, file=sys.stderr)
    sys.exit(1)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyWidget()
    sys.excepthook = exception_hook
    ex.show()
    sys.exit(app.exec_())
