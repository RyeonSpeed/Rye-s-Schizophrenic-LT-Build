## To start

Make sure you are on the `webdev` branch of lt-maker.

`pip install pygbag`

run `pygbag main.py` from this directory or navigate above lt-maker and run `pygbag lt-maker`.

Navigate to `http://localhost:8000` or `http://localhost:8000/?-i` for debugging

# Code changes that have been made from regular LT-maker engine
1. Uses await asyncio
2. all threading is turned off (web does not support it)

## Code changes we previously had to make to get engine working in web but no longer seem necessary
2. colorsys and filecmp are not imported
3. mouse cannot check for focus (always set to True instead)
4. pygame pixel array color modification is replaced with the slower x by y color modification

# Notes
The Engine, even on just the title screen runs 5-6x slower at it's best. I am seeing roughly 30 fps.
Saving will need to be reimagined to work on the browser.

# Giving to other people
You can zip up your `build/web` directory as `web.zip`. Then you can upload it to itch io. Kind of Project should be HTML. When you upload the zip file, make sure to check the option: `This file will be played in the browser`. I set the resolution to 1280x720 and didn't click any of the other optional check boxes

See these instructions (around 3 minutes in) as a video guide: https://www.youtube.com/watch?v=6PhDmpBcezQ

# If you want to do some really simple testing
Simple test code below. Make sure `pygame.png` exists within the directory. Can be any png.

```python
import asyncio
import pygame, random, os, time

pygame.init()
screen = pygame.display.set_mode((400, 400))
snake_head = os.path.join(os.path.dirname(__file__), 'pygame.png')
pygame_head = pygame.image.load(snake_head).convert_alpha()

async def main():
    current_time = time.time()
    current_color = (255, 0, 0)
    done = False
    while not done:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done = True
            elif event.type == pygame.MOUSEBUTTONDOWN:
                current_color = random.sample(range(0, 256), 3)
    
        if time.time() - current_time > 2:
            current_color = random.sample(range(0, 256), 3)
            current_time = time.time()

        screen.fill(current_color)
        screen.blit(pygame_head, (0, 0))
        pygame.display.flip()
        await asyncio.sleep(0)

asyncio.run(main())
pygame.quit()

```
