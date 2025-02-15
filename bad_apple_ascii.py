import cv2
from PIL import Image
import os
import pygame
import time
from collections import deque

ASCII_CHARS = {
    'empty': ' ',           
    'full': '@',            
    'top': '″',            
    'bottom': '_',         
    'left': ')',           
    'right': '(',          
    'top_left': '\\',      
    'top_right': '/',      
    'bottom_left': '/',    
    'bottom_right': '\\',  
    'vertical': '|',       
    'horizontal': '-',     
    'medium': '#',         
}

def init_console():
    if os.name == 'nt':
        os.system('color')
    print('\033[2J', end='')

def move_cursor_to_home():
    print('\033[H', end='')

def resize_image(image, new_width=160):
    width, height = image.size
    new_height = int((height / width) * new_width * 0.45)
    return image.resize((new_width, new_height))

def analyze_context(pixels, x, y, width, height):
    def get_pixel(px, py):
        if 0 <= px < width and 0 <= py < height:
            return pixels[py * width + px]
        return 0

    current = get_pixel(x, y)
    top = get_pixel(x, y-1)
    bottom = get_pixel(x, y+1)
    left = get_pixel(x-1, y)
    right = get_pixel(x+1, y)
    
    v_gradient = bottom - top
    h_gradient = right - left
    
    if current < 50:
        return ASCII_CHARS['empty']
    elif current > 200:
        return ASCII_CHARS['full']
    else:
        if abs(v_gradient) > abs(h_gradient):
            if v_gradient > 50:
                return ASCII_CHARS['bottom']
            elif v_gradient < -50:
                return ASCII_CHARS['top']
            else:
                return ASCII_CHARS['vertical']
        else:
            if h_gradient > 50:
                return ASCII_CHARS['right']
            elif h_gradient < -50:
                return ASCII_CHARS['left']
            else:
                return ASCII_CHARS['horizontal']

def pixels_to_ascii(image):
    width, height = image.size
    pixels = list(image.getdata())
    ascii_str = ""
    
    for y in range(height):
        for x in range(width):
            ascii_str += analyze_context(pixels, x, y, width, height)
    
    return ascii_str

def main():
    video_path = "bad_apple.mp4"
    audio_path = "bad_apple.mp3"

    init_console()
    pygame.init()
    pygame.mixer.init()
    cap = cv2.VideoCapture(video_path)

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_time = 1.0 / fps
    
    frame_buffer = deque(maxlen=5)
    for _ in range(5):
        ret, frame = cap.read()
        if ret:
            im = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
            im = resize_image(im)
            ascii_str = pixels_to_ascii(im)
            frame_buffer.append((ascii_str, im.width))

    pygame.mixer.music.load(audio_path)
    pygame.mixer.music.set_volume(0.2)
    pygame.mixer.music.play()
    
    start_time = time.time()
    frame_count = 0

    while True:
        current_time = time.time() - start_time
        target_frame = int(current_time * fps)
        
        if target_frame > frame_count:
            ret, frame = cap.read()
            if not ret:
                break
                
            im = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
            im = resize_image(im)
            ascii_str = pixels_to_ascii(im)
            frame_buffer.append((ascii_str, im.width))
            frame_count += 1
        
        if frame_buffer:
            ascii_str, width = frame_buffer[0]
            move_cursor_to_home()
            print('\n'.join(ascii_str[i:i+width] for i in range(0, len(ascii_str), width)))
            
            next_frame_time = start_time + (frame_count + 1) * frame_time
            current_time = time.time()
            if next_frame_time > current_time:
                time.sleep(max(0, next_frame_time - current_time))
            
            frame_buffer.popleft()
        
        if not pygame.mixer.music.get_busy():
            break
    
    cap.release()
    pygame.mixer.music.stop()
    pygame.quit()
    print("Воспроизведение завершено")

if __name__ == "__main__":
    main()