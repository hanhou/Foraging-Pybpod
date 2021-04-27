#-------------------------------------------------
#
# Sensapex uMp SDK library (c) 2016 Sensapex oy
#
#-------------------------------------------------

QT    -= core gui

TARGET = ump
TEMPLATE = lib
#CONFIG += staticlib

DEFINES += LIBUMP_LIBRARY

SOURCES += libump.c 

HEADERS += ../../libump.h \
           smcp1.h

INCLUDEPATH += ../..

windows: {
    QMAKE_LINK = $$QMAKE_LINK_C
    LIBS += -lws2_32
    LIBS += -shared
    addFiles.path = .
    addFiles.sources = libump.dll
    DEPLOYMENT += addFiles
}

unix: {
    target.path = /usr/local/lib
    INSTALLS += target
}

mac: {

}

