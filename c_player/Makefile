# Target executable name
TARGET = bin/player.exe

# Compiler and Flags
CC = gcc
CFLAGS = -Wall -O2 -I/mingw64/include
LDFLAGS = -L/mingw64/lib -lmingw32 -lSDL2main -lSDL2 -lavformat -lavcodec -lavutil -lswscale -lswresample -mconsole

# Directories
SRC_DIR = src
BIN_DIR = bin

# Source files
SRCS = $(wildcard $(SRC_DIR)/*.c)
OBJS = $(SRCS:$(SRC_DIR)/%.c=$(BIN_DIR)/%.o)

# Default rule
all: $(BIN_DIR) $(TARGET)

# Create bin directory
$(BIN_DIR):
	@if not exist $(BIN_DIR) mkdir $(BIN_DIR)

# Link the target
$(TARGET): $(OBJS)
	$(CC) $(OBJS) -o $(TARGET) $(LDFLAGS)

# Compile source files
$(BIN_DIR)/%.o: $(SRC_DIR)/%.c
	$(CC) $(CFLAGS) -c $< -o $@

# Clean up
clean:
	@if exist $(BIN_DIR) rd /s /q $(BIN_DIR)
	@if exist tests\bin rd /s /q tests\bin

# Test Outputs
TEST_BIN_DIR = tests/bin
TEST_SYNC = $(TEST_BIN_DIR)/test_sync.exe
TEST_QUEUE = $(TEST_BIN_DIR)/test_packet_queue.exe

# Target for tests
test: $(BIN_DIR) $(TEST_BIN_DIR) $(OBJS) $(TEST_SYNC) $(TEST_QUEUE)
	@echo ----------------------------------------
	@echo Running tests...
	@$(TEST_SYNC)
	@$(TEST_QUEUE)

$(TEST_BIN_DIR):
	-mkdir tests\bin 2>nul

$(TEST_SYNC): tests/test_sync.c $(BIN_DIR)/sync.o
	$(CC) $(CFLAGS) $< $(BIN_DIR)/sync.o -o $@ $(LDFLAGS)

$(TEST_QUEUE): tests/test_packet_queue.c $(BIN_DIR)/packet_queue.o
	$(CC) $(CFLAGS) $< $(BIN_DIR)/packet_queue.o -o $@ $(LDFLAGS)

.PHONY: all clean test
