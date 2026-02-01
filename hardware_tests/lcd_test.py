import time
from RPLCD.i2c import CharLCD

# Constants
I2C_ADDR = 0x27 
LCD_WIDTH = 16 

def scroll_text(lcd, text, row=0, delay=0.3):
    """
    Scrolls text on a specific row of the 16x2 LCD.
    """
    # Pad text with spaces to create a smooth scrolling effect
    padded_text = " " * LCD_WIDTH + text + " " * LCD_WIDTH
    
    try:
        for i in range(len(padded_text) - LCD_WIDTH + 1):
            lcd.cursor_pos = (row, 0)
            lcd.write_string(padded_text[i:i+LCD_WIDTH])
            time.sleep(delay)
    except KeyboardInterrupt:
        pass

def main():
    print(f"Initializing LCD at address {hex(I2C_ADDR)}...")
    try:
        lcd = CharLCD(i2c_expander='PCF8574', address=I2C_ADDR, port=1, cols=16, rows=2, charmap='A00')
        lcd.clear()
        
        print("Displaying static text...")
        lcd.cursor_pos = (0, 0)
        lcd.write_string("LCD Test Mode")
        time.sleep(2)
        
        print("Starting scrolling text demo (Ctrl+C to stop)...")
        while True:
            # Scroll on line 2
            scroll_text(lcd, "Running System Diagnostics... OK", row=1, delay=0.2)
            
            # Change top line
            lcd.cursor_pos = (0, 0)
            lcd.write_string("Status: Active  ")
            
            time.sleep(1)
            
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure I2C is enabled and the address is correct.")
    finally:
        try:
            lcd.clear()
        except:
            pass
        print("\nTest finished.")

if __name__ == "__main__":
    main()
