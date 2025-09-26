"""
NPU Performance Benchmark for Chucksteroids
Tests collision detection and particle update performance
"""

import time
import random
import numpy as np
from typing import List
import matplotlib.pyplot as plt

# Import NPU acceleration modules
try:
    from npu_acceleration import NPUCollisionDetector, NPUDrawingAccelerator
    NPU_AVAILABLE = True
except ImportError:
    NPU_AVAILABLE = False
    print("NPU acceleration not available - running CPU-only benchmark")


class MockGameObject:
    """Mock game object for testing"""
    def __init__(self, x, y, radius):
        self.position = type('Position', (), {'x': x, 'y': y})()
        self.radius = radius
        self.active = True


class MockParticle:
    """Mock particle for testing"""
    def __init__(self, x, y, vx, vy, lifetime):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.lifetime = lifetime


class NPUBenchmark:
    """Comprehensive NPU benchmark suite"""
    
    def __init__(self):
        self.collision_detector = None
        self.drawing_accelerator = None
        
        if NPU_AVAILABLE:
            self.collision_detector = NPUCollisionDetector(use_npu=True)
            self.drawing_accelerator = NPUDrawingAccelerator(use_npu=True)
            print("NPU benchmark initialized")
        else:
            print("NPU benchmark running in CPU-only mode")
        
        self.results = {
            'collision_tests': [],
            'particle_tests': [],
            'scaling_tests': []
        }
    
    def generate_test_objects(self, count: int) -> List[MockGameObject]:
        """Generate test objects for collision detection"""
        objects = []
        for _ in range(count):
            x = random.uniform(0, 1920)
            y = random.uniform(0, 1080)
            radius = random.uniform(10, 50)
            objects.append(MockGameObject(x, y, radius))
        return objects
    
    def generate_test_particles(self, count: int) -> List[MockParticle]:
        """Generate test particles for particle system testing"""
        particles = []
        for _ in range(count):
            x = random.uniform(0, 1920)
            y = random.uniform(0, 1080)
            vx = random.uniform(-100, 100)
            vy = random.uniform(-100, 100)
            lifetime = random.uniform(1, 5)
            particles.append(MockParticle(x, y, vx, vy, lifetime))
        return particles
    
    def benchmark_collision_detection(self, object_counts: List[int], iterations: int = 10):
        """Benchmark collision detection performance"""
        print("\n=== Collision Detection Benchmark ===")
        
        for count in object_counts:
            print(f"\nTesting {count} objects...")
            
            # Generate test objects
            objects1 = self.generate_test_objects(count)
            objects2 = self.generate_test_objects(count)
            
            # Benchmark NPU version
            npu_times = []
            for _ in range(iterations):
                start_time = time.time()
                if self.collision_detector:
                    collisions = self.collision_detector.batch_collision_detection(
                        objects1, objects2, "test_collision"
                    )
                else:
                    # CPU fallback
                    collisions = self._cpu_collision_fallback(objects1, objects2)
                npu_times.append(time.time() - start_time)
            
            avg_npu_time = np.mean(npu_times)
            std_npu_time = np.std(npu_times)
            
            # Benchmark pure CPU version
            cpu_times = []
            for _ in range(iterations):
                start_time = time.time()
                collisions = self._cpu_collision_fallback(objects1, objects2)
                cpu_times.append(time.time() - start_time)
            
            avg_cpu_time = np.mean(cpu_times)
            std_cpu_time = np.std(cpu_times)
            
            speedup = avg_cpu_time / avg_npu_time if avg_npu_time > 0 else 1.0
            
            result = {
                'object_count': count,
                'npu_time': avg_npu_time,
                'npu_std': std_npu_time,
                'cpu_time': avg_cpu_time,
                'cpu_std': std_cpu_time,
                'speedup': speedup,
                'collisions_found': len(collisions)
            }
            
            self.results['collision_tests'].append(result)
            
            print(f"  NPU Time: {avg_npu_time*1000:.2f}ms ± {std_npu_time*1000:.2f}ms")
            print(f"  CPU Time: {avg_cpu_time*1000:.2f}ms ± {std_cpu_time*1000:.2f}ms")
            print(f"  Speedup: {speedup:.2f}x")
            print(f"  Collisions found: {len(collisions)}")
    
    def benchmark_particle_updates(self, particle_counts: List[int], iterations: int = 10):
        """Benchmark particle update performance"""
        print("\n=== Particle Update Benchmark ===")
        
        for count in particle_counts:
            print(f"\nTesting {count} particles...")
            
            # Generate test particles
            particles = self.generate_test_particles(count)
            
            # Benchmark NPU version
            npu_times = []
            for _ in range(iterations):
                start_time = time.time()
                if self.drawing_accelerator:
                    updated_particles = self.drawing_accelerator.batch_particle_update(particles)
                else:
                    # CPU fallback
                    updated_particles = self._cpu_particle_fallback(particles)
                npu_times.append(time.time() - start_time)
            
            avg_npu_time = np.mean(npu_times)
            std_npu_time = np.std(npu_times)
            
            # Benchmark pure CPU version
            cpu_times = []
            for _ in range(iterations):
                start_time = time.time()
                updated_particles = self._cpu_particle_fallback(particles)
                cpu_times.append(time.time() - start_time)
            
            avg_cpu_time = np.mean(cpu_times)
            std_cpu_time = np.std(cpu_times)
            
            speedup = avg_cpu_time / avg_npu_time if avg_npu_time > 0 else 1.0
            
            result = {
                'particle_count': count,
                'npu_time': avg_npu_time,
                'npu_std': std_npu_time,
                'cpu_time': avg_cpu_time,
                'cpu_std': std_cpu_time,
                'speedup': speedup
            }
            
            self.results['particle_tests'].append(result)
            
            print(f"  NPU Time: {avg_npu_time*1000:.2f}ms ± {std_npu_time*1000:.2f}ms")
            print(f"  CPU Time: {avg_cpu_time*1000:.2f}ms ± {std_cpu_time*1000:.2f}ms")
            print(f"  Speedup: {speedup:.2f}x")
    
    def benchmark_scaling(self, max_objects: int = 2000, step: int = 200):
        """Benchmark performance scaling with object count"""
        print("\n=== Performance Scaling Benchmark ===")
        
        object_counts = list(range(step, max_objects + 1, step))
        
        for count in object_counts:
            print(f"Testing {count} objects...")
            
            # Generate test objects
            objects1 = self.generate_test_objects(count)
            objects2 = self.generate_test_objects(count)
            
            # Quick benchmark (fewer iterations for scaling test)
            iterations = 3
            
            # NPU benchmark
            npu_times = []
            for _ in range(iterations):
                start_time = time.time()
                if self.collision_detector:
                    collisions = self.collision_detector.batch_collision_detection(
                        objects1, objects2, "scaling_test"
                    )
                else:
                    collisions = self._cpu_collision_fallback(objects1, objects2)
                npu_times.append(time.time() - start_time)
            
            avg_npu_time = np.mean(npu_times)
            
            # CPU benchmark
            cpu_times = []
            for _ in range(iterations):
                start_time = time.time()
                collisions = self._cpu_collision_fallback(objects1, objects2)
                cpu_times.append(time.time() - start_time)
            
            avg_cpu_time = np.mean(cpu_times)
            speedup = avg_cpu_time / avg_npu_time if avg_npu_time > 0 else 1.0
            
            result = {
                'object_count': count,
                'npu_time': avg_npu_time,
                'cpu_time': avg_cpu_time,
                'speedup': speedup
            }
            
            self.results['scaling_tests'].append(result)
            
            print(f"  NPU: {avg_npu_time*1000:.1f}ms, CPU: {avg_cpu_time*1000:.1f}ms, Speedup: {speedup:.2f}x")
    
    def _cpu_collision_fallback(self, objects1: List, objects2: List) -> List:
        """CPU fallback collision detection"""
        collisions = []
        for obj1 in objects1:
            for obj2 in objects2:
                dx = obj1.position.x - obj2.position.x
                dy = obj1.position.y - obj2.position.y
                distance = np.sqrt(dx*dx + dy*dy)
                if distance < (obj1.radius + obj2.radius):
                    collisions.append((obj1, obj2))
        return collisions
    
    def _cpu_particle_fallback(self, particles: List) -> List:
        """CPU fallback particle update"""
        dt = 0.016  # 60 FPS
        for particle in particles:
            particle.x += particle.vx * dt
            particle.y += particle.vy * dt
            particle.lifetime -= dt
        return particles
    
    def generate_performance_report(self):
        """Generate comprehensive performance report"""
        print("\n" + "="*60)
        print("NPU PERFORMANCE BENCHMARK REPORT")
        print("="*60)
        
        if not NPU_AVAILABLE:
            print("NPU acceleration not available - showing CPU-only results")
        
        # Collision detection summary
        if self.results['collision_tests']:
            print("\nCOLLISION DETECTION PERFORMANCE:")
            print("-" * 40)
            for result in self.results['collision_tests']:
                print(f"{result['object_count']:4d} objects: "
                      f"NPU {result['npu_time']*1000:5.1f}ms, "
                      f"CPU {result['cpu_time']*1000:5.1f}ms, "
                      f"Speedup {result['speedup']:4.2f}x")
        
        # Particle system summary
        if self.results['particle_tests']:
            print("\nPARTICLE UPDATE PERFORMANCE:")
            print("-" * 40)
            for result in self.results['particle_tests']:
                print(f"{result['particle_count']:4d} particles: "
                      f"NPU {result['npu_time']*1000:5.1f}ms, "
                      f"CPU {result['cpu_time']*1000:5.1f}ms, "
                      f"Speedup {result['speedup']:4.2f}x")
        
        # Scaling analysis
        if self.results['scaling_tests']:
            print("\nSCALING ANALYSIS:")
            print("-" * 40)
            avg_speedup = np.mean([r['speedup'] for r in self.results['scaling_tests']])
            max_speedup = max([r['speedup'] for r in self.results['scaling_tests']])
            print(f"Average speedup: {avg_speedup:.2f}x")
            print(f"Maximum speedup: {max_speedup:.2f}x")
        
        print("\n" + "="*60)
    
    def save_results(self, filename: str = "npu_benchmark_results.txt"):
        """Save benchmark results to file"""
        with open(filename, 'w') as f:
            f.write("NPU Benchmark Results\n")
            f.write("====================\n\n")
            
            if self.results['collision_tests']:
                f.write("Collision Detection Results:\n")
                for result in self.results['collision_tests']:
                    f.write(f"Objects: {result['object_count']}, "
                           f"NPU: {result['npu_time']*1000:.2f}ms, "
                           f"CPU: {result['cpu_time']*1000:.2f}ms, "
                           f"Speedup: {result['speedup']:.2f}x\n")
                f.write("\n")
            
            if self.results['particle_tests']:
                f.write("Particle Update Results:\n")
                for result in self.results['particle_tests']:
                    f.write(f"Particles: {result['particle_count']}, "
                           f"NPU: {result['npu_time']*1000:.2f}ms, "
                           f"CPU: {result['cpu_time']*1000:.2f}ms, "
                           f"Speedup: {result['speedup']:.2f}x\n")
                f.write("\n")
        
        print(f"Results saved to {filename}")


def main():
    """Run the NPU benchmark suite"""
    print("Chucksteroids NPU Performance Benchmark")
    print("======================================")
    
    if not NPU_AVAILABLE:
        print("Warning: NPU acceleration not available")
        print("This benchmark will show CPU-only performance")
    
    benchmark = NPUBenchmark()
    
    # Run collision detection benchmark
    collision_counts = [50, 100, 200, 500, 1000]
    benchmark.benchmark_collision_detection(collision_counts, iterations=5)
    
    # Run particle update benchmark
    particle_counts = [100, 200, 500, 1000, 2000]
    benchmark.benchmark_particle_updates(particle_counts, iterations=5)
    
    # Run scaling benchmark
    benchmark.benchmark_scaling(max_objects=1500, step=150)
    
    # Generate report
    benchmark.generate_performance_report()
    benchmark.save_results()
    
    print("\nBenchmark complete!")


if __name__ == "__main__":
    main()
