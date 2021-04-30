#
# Sample C program for Sensapex micromanipulator SDK
# (c) Sensapex 2016
#
# Makefile
#

CC = gcc

CPP_FLAGS += -W -Wall -fPIC -I../..

ifeq ($(debug),1)
	PREFIX=/local
	CPP_FLAGS += -g  -D_DEBUG 
	LDFLAGS   += -L/usr/local/lib
else
	PREFIX=
	CPP_FLAGS += -O2 -DNDEBUG
endif

LIBS =  -L../lib -L/usr/local/lib -lump

SRCS = sample.c

OBJS = $(SRCS:.c=.o)

.c.o: $(HDRS)
	@$(CC) -c $(CPP_FLAGS) $< -o $@

TARGET = sample

# Targets
all: $(TARGET)

$(OBJS): $(SRC) $(HDRS)

install: $(TARGET)
	install -D -v -s $(TARGET) $(DESTDIR)/usr$(PREFIX)/bin/$(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(OBJS) $(LDFLAGS) $(LIBS) -o $(TARGET)

clean:
	rm -f $(TARGET) $(OBJS)

