from PyQt4.QtGui import QFont

monospace_font = QFont('Monospace')
monospace_font.setStyleHint(QFont.TypeWriter)

script_file_filter = 'Coinscripts (*.coinscript);;Text files (*.txt);;All files (*.*)'

hashmal_style = '''

QStatusBar[hasError=true], QLineEdit[hasError=true] {
  background: rgba(255, 0, 0, 25%);
}
'''
