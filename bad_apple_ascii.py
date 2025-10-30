# Константы
VIDEO_PATH = "bad_apple.mp4"
AUDIO_PATH = "bad_apple.mp3"
DEFAULT_WIDTH = 160
FRAME_BUFFER_SIZE = 5
STAR_THRESHOLD = 21
STAR_NEIGHBOR_MAX = 20
EMPTY_THRESHOLD = 10
FULL_THRESHOLD = 200
GRADIENT_STRONG = 50
ASCII_HEIGHT_RATIO = 0.45

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
    'vertical': '|',       
    'horizontal': '-',     
    'star': '.',          # добавлен символ для звезды
}

def init_console():
    """Инициализация консоли для корректного отображения цветов и очистки экрана."""
    if os.name == 'nt':
        os.system('color')
    print('\033[2J', end='')

def move_cursor_to_home():
    """Перемещает курсор в левый верхний угол консоли."""
    print('\033[H', end='')

def resize_image(image, new_width=DEFAULT_WIDTH):
    """Изменяет размер изображения с учетом пропорций для ASCII-графики."""
    width, height = image.size
    new_height = int((height / width) * new_width * ASCII_HEIGHT_RATIO)
    return image.resize((new_width, new_height))

def analyze_context(pixels, x, y, width, height):
    """Анализирует окрестность пикселя и возвращает соответствующий ASCII-символ."""
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

    is_star = current > STAR_THRESHOLD and all(n < STAR_NEIGHBOR_MAX for n in [top, bottom, left, right])
    is_empty = current < EMPTY_THRESHOLD
    is_full = current > FULL_THRESHOLD
    is_vertical = abs(v_gradient) > abs(h_gradient)

    if is_star:
        return ASCII_CHARS['star']
    if is_empty:
        return ASCII_CHARS['empty']
    if is_full:
        return ASCII_CHARS['full']

    if is_vertical:
        if v_gradient > GRADIENT_STRONG:
            return ASCII_CHARS['bottom']
        elif v_gradient < -GRADIENT_STRONG:
            return ASCII_CHARS['top']
        else:
            return ASCII_CHARS['vertical']
    else:
        if h_gradient > GRADIENT_STRONG:
            return ASCII_CHARS['right']
        elif h_gradient < -GRADIENT_STRONG:
            return ASCII_CHARS['left']
        else:
            return ASCII_CHARS['horizontal']

def pixels_to_ascii(image):
    """Преобразует изображение в строку ASCII-символов."""
    width, height = image.size
    pixels = list(image.getdata())
    chars = []
    
    for y in range(height):
        for x in range(width):
            chars.append(analyze_context(pixels, x, y, width, height))
    
    return ''.join(chars)

def main():
    """Основная функция: воспроизводит видео и аудио, отображая ASCII-графику в консоли."""
    init_console()
    pygame.init()
    pygame.mixer.init()
    cap = cv2.VideoCapture(VIDEO_PATH)

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_time = 1.0 / fps
    
    frame_buffer = deque(maxlen=FRAME_BUFFER_SIZE)
    for _ in range(FRAME_BUFFER_SIZE):
        ret, frame = cap.read()
        if not ret:
            break
        im = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        im = resize_image(im)
        ascii_str = pixels_to_ascii(im)
        frame_buffer.append((ascii_str, im.width))

    pygame.mixer.music.load(AUDIO_PATH)
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