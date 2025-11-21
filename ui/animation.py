import time
import math

class Animation:
    def __init__(self,duration=0.3):
        self.animation_list = {}
        self.default_duration = duration
        self.default_operator = Operator.ease_in_quad
        self.direction = 1  # 1 for forward, -1 for backward

    def reset(self,id,current=0):
        '''
        重置动画
        id: 动画id
        '''
        self.animation_list[id] = {
            "current": current,
            "target": 0,
            "duration": self.default_duration,
            "start_time": time.time(),
            "obj": None,  # 存储对象引用
            "attr": None  # 存储属性名
        }

    def update(self):
        '''
        更新动画
        '''
        for id in self.animation_list:
            anim = self.animation_list[id]
            if anim["obj"] is None or anim["attr"] is None:
                continue
            if self.is_running(id):
                # 计算动画结果
                result = self.run(id, anim["target"], anim["duration"], anim["operator"])
                # 设置新值
                setattr(anim["obj"], anim["attr"], result)
    
    def start(self, id, obj, attr, target, duration=None, operator=None):
        '''
        开始动画
        id: 动画id
        obj: 要动画的对象
        attr: 要动画的属性名
        target: 目标值
        duration: 动画时长
        '''
        self.reset(id)
        anim = self.animation_list[id]
        anim["obj"] = obj
        anim["attr"] = attr
        anim["target"] = target
        anim["duration"] = duration if duration is not None else self.default_duration
        anim["current"] = getattr(obj, attr)
        anim["operator"] = operator if operator is not None else self.default_operator
        
    def run(self,id,target,duration = None, operator=None):
        '''
        运行动画
        id: 动画id
        target: 目标值
        duration: 动画时长
        '''
        if duration is None:
            duration = self.default_duration
        
        if self.animation_list[id]["start_time"] > 0:
            elapsed = time.time() - self.animation_list[id]["start_time"]
            if elapsed <= duration:
                current = self.animation_list[id]["current"]
                progress = elapsed / duration
                
                # 使用动画算子
                if operator is None:
                    operator = self.default_operator
                    
                progress = operator(progress) 

                current = current + (target - current) * progress
                self.animation_list[id]["current"] = current
                return current
            else:
                self.animation_list[id]["start_time"] = 0
                return target
        
        return target

    def is_running(self,id):
        '''
        判断动画是否正在运行
        id: 动画id
        '''
        return self.animation_list[id]["start_time"] > 0


class Operator:
    def ease_linear(t):
        """线性缓动"""
        return t

    def ease_in_quad(t):
        """二次方缓入"""
        return t * t

    def ease_out_quad(t):
        """二次方缓出"""
        return t * (2 - t)

    def ease_in_out_quad(t):
        """二次方缓入缓出"""
        return 2 * t * t if t < 0.5 else -1 + (4 - 2 * t) * t

    def ease_in_cubic(t):
        """三次方缓入"""
        return t * t * t

    def ease_out_cubic(t):
        """三次方缓出"""
        return (t - 1) * (t - 1) * (t - 1) + 1

    def ease_in_out_cubic(t):
        """三次方缓入缓出"""
        return 4 * t * t * t if t < 0.5 else (t - 1) * (2 * t - 2) * (2 * t - 2) + 1

    def ease_in_elastic(t):
        """弹性缓入"""
        c4 = (2 * math.pi) / 3
        if t == 0:
            return 0
        if t == 1:
            return 1
        return -pow(2, 10 * t - 10) * math.sin((t * 10 - 10.75) * c4)

    def ease_out_elastic(t):
        """弹性缓出"""
        c4 = (2 * math.pi) / 3
        if t == 0:
            return 0
        if t == 1:
            return 1
        return pow(2, -10 * t) * math.sin((t * 10 - 0.75) * c4) + 1

    def ease_in_out_elastic(t):
        """弹性缓入缓出"""
        c5 = (2 * math.pi) / 4.5
        if t == 0:
            return 0
        if t == 1:
            return 1
        if t < 0.5:
            return -(pow(2, 20 * t - 10) * math.sin((20 * t - 11.125) * c5)) / 2
        return (pow(2, -20 * t + 10) * math.sin((20 * t - 11.125) * c5)) / 2 + 1

    def ease_in_bounce(t):
        """弹跳缓入"""
        return 1 - Operator.ease_out_bounce(1 - t)

    def ease_out_bounce(t):
        """弹跳缓出"""
        n1 = 7.5625
        d1 = 2.75
        if t < 1 / d1:
            return n1 * t * t
        elif t < 2 / d1:
            t -= 1.5 / d1
            return n1 * t * t + 0.75
        elif t < 2.5 / d1:
            t -= 2.25 / d1
            return n1 * t * t + 0.9375
        else:
            t -= 2.625 / d1
            return n1 * t * t + 0.984375

    def ease_in_out_bounce(self, t):
        """弹跳缓入缓出"""
        if t < 0.5:
            return Operator.ease_in_bounce(t * 2) / 2
        return Operator.ease_out_bounce(t * 2 - 1) / 2 + 0.5
