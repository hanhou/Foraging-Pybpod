TARGET = sample
QT =
CONFIG   += console
CONFIG   -= app_bundle
TEMPLATE  = app
SOURCES += sample.c
LIBS    += -L../lib -L/usr/local/lib -lump
INCLUDEPATH += ../..

win32:CONFIG(release, debug|release): LIBS += -L$$PWD/../lib/release/ -lump
else:win32:CONFIG(debug, debug|release): LIBS += -L$$PWD/../lib/debug/ -lump
else:unix: LIBS += -L$$PWD/../lib/ -lump

INCLUDEPATH += $$PWD/../lib
DEPENDPATH += $$PWD/../lib
