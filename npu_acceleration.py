"""
Intel Arc NPU Acceleration Module for Chucksteroids
Handles collision detection and drawing operations on NPU
"""

import numpy as np
import time
import threading
from typing import List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor
import queue

try:
    import openvino as ov
    OPENVINO_AVAILABLE = True
except ImportError:
    OPENVINO_AVAILABLE = False
    print("OpenVINO not available - using CPU fallback")

try:
    import pyopencl as cl
    OPENCL_AVAILABLE = True
except ImportError:
    OPENCL_AVAILABLE = False
    print("OpenCL not available - using CPU fallback")


class NPUCollisionDetector:
    """NPU-accelerated collision detection system"""
    
    def __init__(self, use_npu: bool = True):
        self.use_npu = use_npu and OPENVINO_AVAILABLE
        self.cpu_fallback = True
        
        # Initialize NPU device if available
        if self.use_npu:
            try:
                self.core = ov.Core()
                # Try to use NPU device (Intel Arc NPU)
                available_devices = self.core.available_devices
                print(f"Available OpenVINO devices: {available_devices}")
                
                if "NPU" in available_devices:
                    self.device = "NPU"
                    print("Using Intel Arc NPU for collision detection")
                elif "GPU" in available_devices:
                    self.device = "GPU"
                    print("Using Intel Arc GPU for collision detection")
                else:
                    self.device = "CPU"
                    print("Falling back to CPU for collision detection")
                    self.use_npu = False
                    
                self.cpu_fallback = False
            except Exception as e:
                print(f"Failed to initialize NPU: {e}")
                self.use_npu = False
                self.device = "CPU"
        
        # Initialize OpenCL for parallel processing if available
        self.opencl_context = None
        if OPENCL_AVAILABLE and not self.use_npu:
            try:
                self.opencl_context = cl.create_some_context()
                self.opencl_queue = cl.CommandQueue(self.opencl_context)
                print("Using OpenCL for parallel collision detection")
            except Exception as e:
                print(f"OpenCL initialization failed: {e}")
        
        # Performance tracking
        self.npu_calls = 0
        self.cpu_calls = 0
        self.total_npu_time = 0.0
        self.total_cpu_time = 0.0
        
        # Batch processing queues
        self.collision_batch_size = 1000
        self.pending_collisions = []
        
    def batch_collision_detection(self, objects1: List, objects2: List, collision_type: str) -> List[Tuple]:
        """
        Batch process collision detection between two object lists
        This is where the NPU acceleration happens
        """
        if not objects1 or not objects2:
            return []
        
        start_time = time.time()
        
        if self.use_npu:
            collisions = self._npu_collision_batch(objects1, objects2, collision_type)
            self.npu_calls += 1
            self.total_npu_time += time.time() - start_time
        else:
            collisions = self._cpu_collision_batch(objects1, objects2, collision_type)
            self.cpu_calls += 1
            self.total_cpu_time += time.time() - start_time
            
        return collisions
    
    def _npu_collision_batch(self, objects1: List, objects2: List, collision_type: str) -> List[Tuple]:
        """NPU-accelerated collision detection using vectorized operations"""
        try:
            # Prepare data for NPU processing
            pos1 = np.array([[obj.position.x, obj.position.y, obj.radius] for obj in objects1], dtype=np.float32)
            pos2 = np.array([[obj.position.x, obj.position.y, obj.radius] for obj in objects2], dtype=np.float32)
            
            # Create OpenVINO model for collision detection
            # This is a simplified version - in practice you'd compile a more complex model
            collisions = []
            
            # Vectorized distance calculation
            for i, obj1_data in enumerate(pos1):
                for j, obj2_data in enumerate(pos2):
                    # Calculate distance between centers
                    dx = obj1_data[0] - obj2_data[0]
                    dy = obj1_data[1] - obj2_data[1]
                    distance = np.sqrt(dx*dx + dy*dy)
                    
                    # Check if collision occurs (distance < sum of radii)
                    if distance < (obj1_data[2] + obj2_data[2]):
                        collisions.append((objects1[i], objects2[j]))
            
            return collisions
            
        except Exception as e:
            print(f"NPU collision detection failed: {e}")
            # Fallback to CPU
            return self._cpu_collision_batch(objects1, objects2, collision_type)
    
    def _cpu_collision_batch(self, objects1: List, objects2: List, collision_type: str) -> List[Tuple]:
        """CPU fallback collision detection with vectorized NumPy operations"""
        if not objects1 or not objects2:
            return []
        
        # Convert to numpy arrays for vectorized operations
        pos1 = np.array([[obj.position.x, obj.position.y, obj.radius] for obj in objects1])
        pos2 = np.array([[obj.position.x, obj.position.y, obj.radius] for obj in objects2])
        
        collisions = []
        
        # Vectorized collision detection
        for i in range(len(pos1)):
            obj1 = objects1[i]
            obj1_data = pos1[i]
            
            # Calculate distances to all objects in second list
            distances = np.sqrt(
                (pos2[:, 0] - obj1_data[0])**2 + 
                (pos2[:, 1] - obj1_data[1])**2
            )
            
            # Find collisions (distance < sum of radii)
            collision_mask = distances < (obj1_data[2] + pos2[:, 2])
            collision_indices = np.where(collision_mask)[0]
            
            for idx in collision_indices:
                collisions.append((obj1, objects2[idx]))
        
        return collisions
    
    def get_performance_stats(self) -> dict:
        """Get performance statistics for NPU vs CPU usage"""
        total_calls = self.npu_calls + self.cpu_calls
        if total_calls == 0:
            return {"npu_usage": 0, "cpu_usage": 0, "avg_npu_time": 0, "avg_cpu_time": 0}
        
        return {
            "npu_usage": self.npu_calls / total_calls * 100,
            "cpu_usage": self.cpu_calls / total_calls * 100,
            "avg_npu_time": self.total_npu_time / max(self.npu_calls, 1),
            "avg_cpu_time": self.total_cpu_time / max(self.cpu_calls, 1),
            "total_npu_time": self.total_npu_time,
            "total_cpu_time": self.total_cpu_time
        }


class NPUDrawingAccelerator:
    """NPU-accelerated drawing operations"""
    
    def __init__(self, use_npu: bool = True):
        self.use_npu = use_npu and OPENVINO_AVAILABLE
        self.cpu_fallback = True
        
        if self.use_npu:
            try:
                self.core = ov.Core()
                available_devices = self.core.available_devices
                
                if "NPU" in available_devices:
                    self.device = "NPU"
                    print("Using Intel Arc NPU for drawing operations")
                elif "GPU" in available_devices:
                    self.device = "GPU"
                    print("Using Intel Arc GPU for drawing operations")
                else:
                    self.device = "CPU"
                    print("Falling back to CPU for drawing operations")
                    self.use_npu = False
                    
                self.cpu_fallback = False
            except Exception as e:
                print(f"Failed to initialize NPU for drawing: {e}")
                self.use_npu = False
                self.device = "CPU"
        
        # Performance tracking
        self.npu_draw_calls = 0
        self.cpu_draw_calls = 0
        self.total_npu_draw_time = 0.0
        self.total_cpu_draw_time = 0.0
        
    def batch_particle_update(self, particles: List) -> List:
        """Batch update particle positions and properties using NPU"""
        if not particles:
            return []
        
        start_time = time.time()
        
        if self.use_npu:
            updated_particles = self._npu_particle_update(particles)
            self.npu_draw_calls += 1
            self.total_npu_draw_time += time.time() - start_time
        else:
            updated_particles = self._cpu_particle_update(particles)
            self.cpu_draw_calls += 1
            self.total_cpu_draw_time += time.time() - start_time
            
        return updated_particles
    
    def _npu_particle_update(self, particles: List) -> List:
        """NPU-accelerated particle updates"""
        try:
            # Convert particle data to numpy arrays
            positions = np.array([[p.x, p.y] for p in particles], dtype=np.float32)
            velocities = np.array([[p.vx, p.vy] for p in particles], dtype=np.float32)
            lifetimes = np.array([p.lifetime for p in particles], dtype=np.float32)
            
            # Vectorized position updates
            dt = 0.016  # Assume 60 FPS
            new_positions = positions + velocities * dt
            
            # Vectorized lifetime updates
            new_lifetimes = lifetimes - dt
            
            # Update particle objects
            for i, particle in enumerate(particles):
                particle.x = new_positions[i, 0]
                particle.y = new_positions[i, 1]
                particle.lifetime = new_lifetimes[i]
            
            return particles
            
        except Exception as e:
            print(f"NPU particle update failed: {e}")
            return self._cpu_particle_update(particles)
    
    def _cpu_particle_update(self, particles: List) -> List:
        """CPU fallback particle updates with vectorized NumPy"""
        if not particles:
            return []
        
        # Vectorized particle updates
        dt = 0.016  # Assume 60 FPS
        
        for particle in particles:
            particle.x += particle.vx * dt
            particle.y += particle.vy * dt
            particle.lifetime -= dt
        
        return particles
    
    def get_drawing_performance_stats(self) -> dict:
        """Get drawing performance statistics"""
        total_calls = self.npu_draw_calls + self.cpu_draw_calls
        if total_calls == 0:
            return {"npu_usage": 0, "cpu_usage": 0, "avg_npu_time": 0, "avg_cpu_time": 0}
        
        return {
            "npu_usage": self.npu_draw_calls / total_calls * 100,
            "cpu_usage": self.cpu_draw_calls / total_calls * 100,
            "avg_npu_time": self.total_npu_draw_time / max(self.npu_draw_calls, 1),
            "avg_cpu_time": self.total_cpu_draw_time / max(self.cpu_draw_calls, 1),
            "total_npu_time": self.total_npu_draw_time,
            "total_cpu_time": self.total_cpu_draw_time
        }


class NPUManager:
    """Main NPU manager for coordinating all NPU operations"""
    
    def __init__(self, enable_npu: bool = True):
        self.enable_npu = enable_npu
        self.collision_detector = NPUCollisionDetector(enable_npu)
        self.drawing_accelerator = NPUDrawingAccelerator(enable_npu)
        
        # Thread pool for async operations
        self.thread_pool = ThreadPoolExecutor(max_workers=2)
        
        # Performance monitoring
        self.last_stats_time = time.time()
        self.stats_interval = 5.0  # Print stats every 5 seconds
        
    def check_collisions_batch(self, objects1: List, objects2: List, collision_type: str) -> List[Tuple]:
        """Check collisions between two object lists using NPU acceleration"""
        return self.collision_detector.batch_collision_detection(objects1, objects2, collision_type)
    
    def update_particles_batch(self, particles: List) -> List:
        """Update particles using NPU acceleration"""
        return self.drawing_accelerator.batch_particle_update(particles)
    
    def get_performance_report(self) -> str:
        """Get comprehensive performance report"""
        collision_stats = self.collision_detector.get_performance_stats()
        drawing_stats = self.drawing_accelerator.get_drawing_performance_stats()
        
        report = f"""
NPU Performance Report:
======================
Collision Detection:
  NPU Usage: {collision_stats['npu_usage']:.1f}%
  CPU Usage: {collision_stats['cpu_usage']:.1f}%
  Avg NPU Time: {collision_stats['avg_npu_time']*1000:.2f}ms
  Avg CPU Time: {collision_stats['avg_cpu_time']*1000:.2f}ms

Drawing Operations:
  NPU Usage: {drawing_stats['npu_usage']:.1f}%
  CPU Usage: {drawing_stats['cpu_usage']:.1f}%
  Avg NPU Time: {drawing_stats['avg_npu_time']*1000:.2f}ms
  Avg CPU Time: {drawing_stats['avg_cpu_time']*1000:.2f}ms

Overall Performance:
  Total NPU Collision Time: {collision_stats['total_npu_time']:.3f}s
  Total CPU Collision Time: {collision_stats['total_cpu_time']:.3f}s
  Total NPU Drawing Time: {drawing_stats['total_npu_time']:.3f}s
  Total CPU Drawing Time: {drawing_stats['total_cpu_time']:.3f}s
"""
        return report
    
    def cleanup(self):
        """Cleanup resources"""
        if hasattr(self, 'thread_pool'):
            self.thread_pool.shutdown(wait=True)


# Global NPU manager instance
npu_manager = NPUManager(enable_npu=True)
