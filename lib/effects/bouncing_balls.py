from lib.led import EffectBase
import time

class BouncingBalls(EffectBase):
    """
    Simulates multi-colored balls bouncing under gravity.
    """
    def _run(self):
        # Physics Constants
        gravity = -5.81  # m/s^2 equivalent
        start_height = 1 # Normalized height (1 = top of strip)
        impact_velocity_start = 0 
        dampening = 0.90 # Energy lost on bounce
        
        # Configuration
        num_balls = 3
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)] # RGB for each ball
        
        # State tracking
        clock_times = [0.0] * num_balls
        start_times = [0.0] * num_balls
        velocities = [0.0] * num_balls
        heights = [start_height] * num_balls
        
        # Stagger the start times slightly so they don't all drop at once
        now = time.time()
        for i in range(num_balls):
            start_times[i] = now + (i * 0.5) # 0.5 sec delay between drops
            velocities[i] = 0.0

        while not self.stopped.is_set():
            now = time.time()
            self.led.clear()
            
            for i in range(num_balls):
                # Calculate time since this ball started dropping
                t = now - start_times[i]
                
                # If ball hasn't started dropping yet, skip
                if t < 0: continue

                # Physics: Calculate height based on gravity
                # h = h0 + v0*t + 0.5*g*t^2
                h = 0.5 * gravity * pow(t, 2) + velocities[i] * t + heights[i]
                
                # Floor collision detection
                if h < 0:
                    h = 0
                    # Bounce!
                    # Calculate velocity at impact: v = v0 + gt
                    v_impact = velocities[i] + gravity * t
                    
                    # Reverse velocity and apply dampening (energy loss)
                    new_v = -v_impact * dampening
                    
                    # Reset simulation for this ball with new initial parameters
                    start_times[i] = now
                    heights[i] = 0
                    velocities[i] = new_v
                    
                    # If velocity is too low, reset the ball to top (infinite loop)
                    if new_v < 1.0: 
                        heights[i] = start_height
                        velocities[i] = 0
                        start_times[i] = now + 1.0 # Pause briefly at top

                # Map height (0.0 to 1.0) to pixel position
                position = int(h * (self.led.count - 1))
                
                # Draw
                if 0 <= position < self.led.count:
                    self.led.set_pixel(position, colors[i % len(colors)])

            self.led.show()
            
            if self.stopped.wait(0.02):
                return
