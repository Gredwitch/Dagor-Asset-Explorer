import sys
# from os import path

# fp = path.dirname(path.abspath(__file__))

# sys.path.append(path.join(fp, "gui"))
# sys.path.append(path.join(fp, "parse"))
# sys.path.append(path.join(fp, "util"))

from gui import app

sys.excepthook = lambda cls, e, t: sys.__excepthook__(cls, e, t)

app = app.App(sys.argv)

exitCode = app.exec_()

sys.exit(exitCode)