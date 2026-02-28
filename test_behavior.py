import sys, os
sys.path.append(r'd:\\Project_Jager\\GithHub_Codes\\GoogleMap\\Jager_Map_integration')
from hardware_tests.behavior_controller import BehaviorController

class MockCar:
    def set_speed(self, s):
        print('Car speed set to', s)
    def set_steering(self, a):
        print('Car steering set to', a)
    def stop(self):
        print('Car stopped')

class MockFusion:
    def __init__(self):
        self.data = {'fused_yaw': 0.0, 'fused_speed': 0.0}
    def get_data(self):
        return self.data
    def update(self, imu_yaw, gps_heading, gps_speed):
        # Simple simulation: fused_yaw = imu_yaw, fused_speed = gps_speed
        self.data['fused_yaw'] = imu_yaw
        self.data['fused_speed'] = gps_speed

# Instantiate controller
fusion = MockFusion()
car = MockCar()
controller = BehaviorController(car, fusion, None)

# Test forward
controller.set_state('FORWARD')
controller.update()

# Simulate speed approaching target
for speed in [10, 30, 50, 70, 90, 100]:
    fusion.update(0.0, 0.0, speed)
    controller.update()

# Test turn left 90
controller.set_state('TURN_LEFT_90')
for yaw in [0, -30, -60, -90]:
    fusion.update(yaw, 0.0, 0.0)
    controller.update()

print('Test completed')
