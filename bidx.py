import sys
import requests
from bs4 import BeautifulSoup
import csv
import json
import sqlite3
import smtplib
from PyQt4.QtGui import *
from PyQt4.QtCore import *
import time

class MyWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setupUI()

    def setupUI(self):
        self.setGeometry(800, 200, 360, 240)
        self.setWindowTitle("New bidx search v1.0")

        font = QFont("Arial", 12)
        font2 = QFont("Arial", 14, QFont.Bold)
        self.setFont(font)

        filename = QHBoxLayout()
        lblFileName = QLabel("File Name : ")
        self.lblFileNameText = QLabel(self)
        filename.addWidget(lblFileName)
        filename.addWidget(self.lblFileNameText)

        login = QGridLayout()
        self.senderEmail = QLabel("Sender Email : ")
        self.senderPassword = QLabel("Password : ")
        self.smtpServer = QLabel("SMTP Server : ")
        self.editSenderEmail = QLineEdit()
        self.editSenderPassword = QLineEdit()
        self.editSmtpServer = QLineEdit()
        self.editSmtpServer.setPlaceholderText("smtp-mail.outlook.com:587")
        login.addWidget(self.senderEmail, 0, 0)
        login.addWidget(self.editSenderEmail, 0, 1)
        login.addWidget(self.senderPassword, 1, 0)
        login.addWidget(self.editSenderPassword, 1, 1)
        login.addWidget(self.smtpServer, 2, 0)
        login.addWidget(self.editSmtpServer, 2, 1)

        buttons = QHBoxLayout()
        btnSend = QPushButton("SEND")
        btnCancel = QPushButton("CANCEL")
        buttons.addWidget(btnSend)
        btnSend.clicked.connect(self.btnSendClicked)
        buttons.addWidget(btnCancel)
        btnCancel.clicked.connect(self.btnCancelClicked)

        title = QLabel("NEW BIDX SEARCH", self)
        title.setFont(font2)

        fileButton = QPushButton("CSV File Open")
        fileButton.clicked.connect(self.fileButtonClicked)

        self.lblStatusText = QLabel(self)

        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addWidget(fileButton)
        layout.addLayout(filename)
        layout.addLayout(login)
        layout.addLayout(buttons)
        layout.addWidget(self.lblStatusText)

        self.setLayout(layout)
        self.show()

    def fileButtonClicked(self):
        fname = QFileDialog.getOpenFileName(self)
        self.lblFileNameText.setText(fname)

    def btnCancelClicked(self):
        self.close()

    def btnSendClicked(self):
        file = self.lblFileNameText.text()
        sender_email = self.editSenderEmail.text()
        password = self.editSenderPassword.text()
        smtpserver = self.editSmtpServer.text()
        if file == '' :
            QMessageBox.about(self, "message", "Please select a csv file!")
            return

        if sender_email == '' :
            QMessageBox.about(self, "message", "Please enter sender email address.")
            self.editSenderEmail.setFocus()
            return

        if password == '':
            QMessageBox.about(self, "message", "Please enter password.")
            self.editSenderPassword.setFocus()
            return

        if smtpserver == '':
            QMessageBox.about(self, "message", "Please enter SMTP Server information.")
            self.editSmtpServer.setFocus()
            return

        #Create DB
        conn = sqlite3.connect('findres.db')
        conn.execute('''CREATE TABLE IF NOT EXISTS `findresult` (
        	`id`    INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        	`url` 	TEXT NOT NULL,
        	`link`  TEXT NOT NULL,
        	`regdate` TEXT NOT NULL
        );''')
        #self.lblStatusText.setText("Table created successfully")

        #Login
        c = requests.Session()
        URL = 'https://bidx.com/site/home'
        html = c.get(URL).text  # sets cookie
        # get token
        soup = BeautifulSoup(html, "html.parser")
        csrf = soup.find("meta", {"name": "csrf_token"})['content']
        payload = {
            'email': 'will@pdpassociates.com',
            'password': 'm*OL47c#',
            'action': 'Log In',
            'referer': 'https://bidx.com/site/home',
            'csrftoken': csrf,
            'max_mysql_date': '2037-12-31'
        }
        c.post('https://bidx.com/site/home', data=payload)
        self.lblStatusText.setText("loged in bidx.xom")
        #r = c.get("https://bidx.com/ct/search")
        #print(r.text)

        #Read CSV file

        with open(file, newline='') as f:
            reader = csv.reader(f)
            for row in reader:
                receiver = row[0]
                search_url = row[1]
                title = row[2]
                keywords = row[3]
                email_body = title + '<br><table>';

                # search request
                search_form = {
                    'action': 'item',
                    'has_advanced': '1',
                    'search_id': 'item',
                    'fulltext': keywords,
                    'offset': '0',
                    'sortcol': 'lettingdate',
                    'sortorder': '1'
                }

                res = c.post(
                    search_url,
                    data=search_form,
                    headers={
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                )
                jsonresult = res.text
                # search result parsing
                html = json.loads(jsonresult)
                htmldata = html['html']
                count = html['count']

                self.lblStatusText.setText("Searching...")


                if int(count) > 20:
                    total = int(count) // 20 + 1
                    for i in range(1, total):
                        offset = i * 20
                        search_form = {
                            'action': 'item',
                            'has_advanced': '1',
                            'search_id': 'item',
                            'fulltext': keywords,
                            'offset': offset,
                            'sortcol': 'lettingdate',
                            'sortorder': '1'
                        }
                        res = c.post(
                            search_url,
                            data=search_form,
                            headers={
                                'X-Requested-With': 'XMLHttpRequest'
                            }
                        )
                        jsonresult = res.text
                        tmphtml = json.loads(jsonresult)
                        soup = BeautifulSoup(tmphtml['html'])
                        for tr in soup.findAll('tr'):
                            for link in tr.findAll('a'):
                                href = link.get('href')
                                cursor = conn.execute(
                                    "SELECT COUNT(*)  from findresult where url='" + search_url + "' and link='" + href + "'")
                                result = cursor.fetchone()
                                number_of_rows = result[0]
                                if number_of_rows == 0:
                                    cursor.execute("Insert into findresult (url,link, regdate) values (?,?,?)", (search_url, href, time.strftime("%Y-%m-%d")))
                                    conn.commit()
                                    email_body += str(tr)

                else:
                    soup = BeautifulSoup(htmldata, "html.parser")
                    for tr in soup.findAll('tr'):
                        for link in tr.findAll('a'):
                            href = link.get('href')
                            link['href'] = 'https://bidx.com' + href
                            cursor = conn.execute(
                                "SELECT COUNT(*)  from findresult where url='" + search_url + "' and link='" + href + "'")
                            result = cursor.fetchone()
                            number_of_rows = result[0]
                            if number_of_rows == 0:
                                cursor.execute("Insert into findresult (url,link,regdate) values (?,?,?)", (search_url, href, time.strftime("%Y-%m-%d")))
                                conn.commit()
                                email_body += str(tr)


            #sender = self.senderEmail.text()
            # receiver = to_email
            #receiver = 'ionel.marine@hotmail.com'
            self.lblStatusText.setText("Sending Email...")
            if email_body == (title + '<br><table>'):
                email_body += '<tr><td align=center>No new items.</td></tr>'

            # print(email_body)

            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            message = MIMEMultipart()
            message['From'] = sender_email
            message['To'] = receiver
            message['Subject'] = 'Subject: New Bidx Search Results'
            message['Title'] = title

            email_body += '</table>'
            message.attach(MIMEText(email_body, 'html'))

            msg = message.as_string()
            smtpObj = smtplib.SMTP("smtp-mail.outlook.com:587")
            smtpObj.starttls()
            smtpObj.login("martinreznicek@hotmail.com", "ehddulfud_12")
            smtpObj.sendmail(sender_email, receiver, msg)
            print("Successfully sent email")
            smtpObj.quit()

            self.lblStatusText.setText("Successfully sent email")

        #self.close()



if __name__ == "__main__":
    app = QApplication(sys.argv)
    mywindow = MyWindow()
    app.exec_()