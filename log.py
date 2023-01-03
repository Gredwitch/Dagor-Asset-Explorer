# from colorama import Fore
from time import time
from enums import *

startTime = time()

def getTime():
    return "%08.4f" % (time() - startTime)

curLevel = 0
levelStr = ""

def incrLevel(level:int = 0):
    global curLevel
    global levelStr

    curLevel += level
    levelStr = ""

    if curLevel < 0:
        level = 0

    for i in range(curLevel):
        levelStr += "    "

def addLevel(level:int = 1):
    incrLevel(level)

def subLevel(level:int = 1):
    incrLevel(-level)


def getLevelStr():
    global levelStr

    return levelStr

def log(message:str, type:int = 0):
    # pass
    if type != LOG_DEBUG:
        if type == LOG_WARN:
            print(f"{getTime()} [W] | {getLevelStr()}{message}")

            return
        elif type == LOG_ERROR:
            print(f"{getTime()} [E] | {getLevelStr()}{message}")

            return
    print(f"{getTime()} [D] | {getLevelStr()}{message}")
