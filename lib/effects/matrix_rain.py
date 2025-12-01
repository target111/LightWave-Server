from lib.led import EffectBase
import random

class MatrixRain(EffectBase):
    """
    Green 'code' drops that are guaranteed to reach the bottom of the strip.
    """
    def _run(self):
        # Configuration
        spawn_rate = 0.05       # Chance of a new drop spawning
        min_speed = 0.2         # Pixels per frame
        max_speed = 0.8
        trail_length = 20       # Length of the trail in pixels
        
        # Color configuration
        head_color = (180, 255, 180) # Whitish Green for the leading bit
        tail_color = (0, 255, 0)     # Standard Matrix Green
        
        # State: List of drops. Each drop is [position, speed]
        drops = []

        while not self.stopped.is_set():
            # 1. Spawn new drops
            if random.random() < spawn_rate:
                # Start just above the top
                drops.append([0.0, random.uniform(min_speed, max_speed)])
            
            # 2. Logic Update
            # We use a dictionary to store the calculated brightness of each pixel
            # This handles overlapping drops gracefully (brightest wins)
            pixel_buffer = {}
            
            active_drops = []
            
            for drop in drops:
                pos, speed = drop
                
                # Move the drop
                pos += speed
                
                # Calculate the trail
                # The 'head' is at the current position.
                # We draw backwards from the head.
                head_pixel = int(pos)
                
                # Optimization: Only process if the drop is still visible
                # It is visible if the head is on screen OR if the tail is still on screen
                if head_pixel - trail_length < self.led.count:
                    active_drops.append([pos, speed])
                    
                    # Draw the trail for this drop
                    for i in range(trail_length):
                        pixel_index = head_pixel - i
                        
                        # Check bounds
                        if 0 <= pixel_index < self.led.count:
                            # Calculate intensity (1.0 at head, 0.0 at tail end)
                            intensity = 1.0 - (i / trail_length)
                            
                            # Store the max intensity for this pixel
                            # (If two drops cross, we want the brighter value)
                            current_val = pixel_buffer.get(pixel_index, 0.0)
                            pixel_buffer[pixel_index] = max(current_val, intensity)
            
            # Keep only active drops
            drops = active_drops

            # 3. Render
            # We construct the frame and send it
            for i in range(self.led.count):
                if i in pixel_buffer:
                    intensity = pixel_buffer[i]
                    
                    # Determine color based on intensity
                    # High intensity (>0.9) gets the Head Color (White-ish)
                    if intensity > 0.9:
                        r = int(head_color[0] * intensity)
                        g = int(head_color[1] * intensity)
                        b = int(head_color[2] * intensity)
                    else:
                        r = int(tail_color[0] * intensity)
                        g = int(tail_color[1] * intensity)
                        b = int(tail_color[2] * intensity)
                        
                    self.led.set_pixel(i, (r, g, b))
                else:
                    # Black out pixels with no drops
                    self.led.set_pixel(i, (0, 0, 0))

            self.led.show()
            
            # Short wait for animation loop
            if self.stopped.wait(0.02):
                return
