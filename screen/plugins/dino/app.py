import time
import random
from screen.base import DisplayPlugin
from until.keymap import get_keymap

# 游戏参数
WIDTH = 128
DINO_WIDTH = 20
DINO_HEIGHT = 22
OBSTACLE_WIDTH = 4
OBSTACLE_MIN_HEIGHT = 6
OBSTACLE_MAX_HEIGHT = 12
GRAVITY = 0.6 # 稍微增加重力
JUMP_FORCE = -6 # 稍微增加跳跃力度
SAFE_DISTANCE = 20  # AI 判断跳跃的安全距离

DINO_HEAD1 = [    
    [0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,0],
    [0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1],
    [0,0,0,0,0,0,0,0,0,0,1,1,0,1,1,1,1,1,1,1],
    [0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1],
    [0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1],
    [0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1],
    [0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,0,0]
]

DINO_HEAD2 = [    
    [0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,0],
    [0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1],
    [0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,1,1,1,1,1],
    [0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1],
    [0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1],
    [0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1],
    [0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,0,0],
    [0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,0,0]
]

# 恐龙基础形状（共同部分）
DINO_BODY = [
    [1,0,0,0,0,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0],
    [1,0,0,0,0,0,0,0,1,1,1,1,1,1,0,0,0,0,0,0],
    [1,1,0,0,0,0,1,1,1,1,1,1,1,1,1,1,0,0,0,0],
    [1,1,1,0,0,1,1,1,1,1,1,1,1,1,0,1,0,0,0,0],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0],
    [0,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0],
    [0,0,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0],
    [0,0,0,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0],
    [0,0,0,0,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0],
]

# 第一帧特有的腿部
DINO_LEGS1 = [
    [0,0,0,0,0,1,1,1,0,0,1,1,1,0,0,0,0,0,0,0],
    [0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0],
]

# 第二帧特有的腿部
DINO_LEGS2 = [
    [0,0,0,0,0,1,1,0,0,1,1,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,1,1,0,0,1,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0],
]

# 碰撞状态特有的腿部
DINO_LEGS3 = [
    [0,0,0,0,0,1,1,1,0,1,1,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,1,1,0,0,0,1,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,1,0,0,0,0,1,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,1,1,0,0,0,1,1,0,0,0,0,0,0,0,0],
]

# 仙人掌图案 - 12像素高
CACTUS_SPRITE_12 = [
    [0,0,1,0],
    [1,0,1,0],
    [1,0,1,0],
    [1,1,1,0],
    [0,1,1,1],
    [0,1,1,1],
    [0,1,1,0],
    [1,1,1,0],
    [1,1,1,0],
    [0,1,1,1],
    [0,1,1,0],
    [0,1,1,0],
]

# 仙人掌图案 - 9像素高
CACTUS_SPRITE_9 = [
    [0,0,1,0],
    [0,0,1,0],
    [1,0,1,0],
    [1,1,1,0],
    [0,1,0,0],
    [0,1,0,1],
    [0,1,1,1],
    [0,1,1,0],
    [0,1,1,0],
]

# 仙人掌图案 - 6像素高
CACTUS_SPRITE_6 = [
    [0,0,1,0],
    [0,0,1,1],
    [1,0,1,0],
    [0,1,1,0],
    [0,0,1,0],
    [0,0,1,0],
]

GAME_FPS = 25.0

# 云朵精灵图
CLOUD_SPRITE = [
    [0,0,1,1,1,1,0,0,0,0],
    [0,1,1,1,1,1,1,1,0,0],
    [1,1,1,1,1,1,1,1,1,0],
    [1,1,1,1,1,1,1,1,1,1],
]

def get_dino_sprite(type):
    # 选择头部
    head = DINO_HEAD1 if type in [1, 2] else DINO_HEAD2
    # 选择腿部
    legs = DINO_LEGS1 if type == 1 else (DINO_LEGS2 if type == 2 else DINO_LEGS3)
    
    # 组合完整的精灵图
    sprite = []
    sprite.extend(head)  # 添加头部
    sprite.extend(DINO_BODY)  # 添加身体
    sprite.extend(legs)  # 添加腿部
    return sprite

class DinoGame:
    def __init__(self, ground_y):
        self.ground_y = ground_y
        self.x = 10
        self.y = self.ground_y - DINO_HEIGHT
        self.velocity = 0
        self.is_jumping = False
        self.leg_state = 0
        self.leg_timer = 0
        self.animation_speed = 4
        self.is_crashed = False  # 添加碰撞状态

    def jump(self):
        if not self.is_jumping and not self.is_crashed:  # 碰撞后不能跳跃
            self.velocity = JUMP_FORCE
            self.is_jumping = True

    def update(self):
        if self.is_crashed:  # 碰撞后不更新位置
            return

        self.velocity += GRAVITY
        self.y += self.velocity
        if self.y > self.ground_y - DINO_HEIGHT:
            self.y = self.ground_y - DINO_HEIGHT
            self.velocity = 0
            self.is_jumping = False

        if not self.is_jumping:
            self.leg_timer += 1
            if self.leg_timer >= self.animation_speed:
                self.leg_state = 1 - self.leg_state
                self.leg_timer = 0

    def draw(self, draw):
        # 选择当前动画帧
        if self.is_crashed:
            sprite = get_dino_sprite(3)  # 碰撞状态
        else:
            sprite = get_dino_sprite(1 if self.leg_state == 0 else 2)  # 正常奔跑状态
        
        # 绘制恐龙
        x_start = int(round(self.x))
        y_start = int(round(self.y))
        
        for i in range(DINO_HEIGHT):
            for j in range(DINO_WIDTH):
                if sprite[i][j]:
                    draw.point((x_start + j, y_start + i), fill=255)


class Obstacle:
    def __init__(self, ground_y):
        self.ground_y = ground_y
        self.x = WIDTH
        self.height = random.randint(OBSTACLE_MIN_HEIGHT, OBSTACLE_MAX_HEIGHT)
        # 根据高度选择最接近的仙人掌图案
        if self.height >= 11:
            self.height = 12
            self.sprite = CACTUS_SPRITE_12
        elif self.height >= 8:
            self.height = 9
            self.sprite = CACTUS_SPRITE_9
        else:
            self.height = 6
            self.sprite = CACTUS_SPRITE_6
        self.y = self.ground_y - self.height
        self.width = OBSTACLE_WIDTH
        self.speed = 3

    def update(self):
        self.x -= self.speed
        return self.x < -self.width

    def draw(self, draw):
        # 绘制仙人掌
        for i in range(self.height):
            for j in range(self.width):
                if self.sprite[i][j]:
                    draw.point((int(self.x) + j, int(self.y) + i), fill=255)

class Cloud:
    def __init__(self, height):
        self.x = WIDTH + random.randint(0, 50)
        self.y = random.randint(4, max(5, height // 3))  # 云朵在屏幕上方1/3区域
        self.width = 10
        self.height = 4
        self.speed = 0.5

    def update(self):
        self.x -= self.speed
        return self.x < -self.width

    def draw(self, draw):
        for i in range(self.height):
            for j in range(self.width):
                if CLOUD_SPRITE[i][j]:
                    draw.point((int(self.x) + j, int(self.y) + i), fill=255)

# 恐龙游戏显示类
class dino(DisplayPlugin):
    def __init__(self, manager, width, height):
        self.name = "dino"
        super().__init__(manager, width, height)
        self.framerate = GAME_FPS
         # 30fps = 33.33ms 每帧
        self.keymap = get_keymap()
        self.screen_height = height
        self.ground_y = height - 1  # 地面在底部
        self.reset_game()

    def reset_game(self, player="AI"):
        self.dino = DinoGame(self.ground_y)
        self.obstacles = []
        self.clouds = [] if self.screen_height > 32 else None  # 只有高度超过32才有云
        self.score = 0
        self.game_over = False
        self.last_jump_time = 0
        self.jump_cooldown = 0.3
        self.frame_count = 0
        self.last_score_update = time.time()
        self.game_over_time = 0  # 记录游戏结束的时间
        self.player = player

    def ai_decision(self):
        current_time = time.time()
        if current_time - self.last_jump_time < self.jump_cooldown:
            return

        # 找到最近的障碍物
        nearest_obstacle = None
        min_distance = float('inf')
        for obstacle in self.obstacles:
            # 考虑恐龙宽度进行距离计算
            distance = obstacle.x - (self.dino.x + DINO_WIDTH)
            if 0 < distance < min_distance:
                min_distance = distance
                nearest_obstacle = obstacle

        # 如果障碍物在安全距离内且恐龙在地面上，就跳跃
        if nearest_obstacle and min_distance < SAFE_DISTANCE and not self.dino.is_jumping:
            self.dino.jump()
            self.last_jump_time = current_time

    def spawn_obstacle(self):
        # 根据帧数调整障碍物生成
        if random.random() < 0.03 and (not self.obstacles or self.obstacles[-1].x < WIDTH - 50):  # 将最小距离从40增加到50
            self.obstacles.append(Obstacle(self.ground_y))

    def spawn_cloud(self):
        # 只有当高度超过32且云数量少于3时才生成
        if self.clouds is not None and len(self.clouds) < 3:
            if random.random() < 0.01:  # 较低的生成概率
                self.clouds.append(Cloud(self.screen_height))

    def check_collision(self):
        dino_rect = (self.dino.x, self.dino.y, 
                     self.dino.x + DINO_WIDTH, self.dino.y + DINO_HEIGHT)
        for obstacle in self.obstacles:
            obs_rect = (obstacle.x, obstacle.y,
                        obstacle.x + obstacle.width,
                        obstacle.y + obstacle.height)
            if (dino_rect[0] < obs_rect[2] and
                dino_rect[2] > obs_rect[0] and
                dino_rect[1] < obs_rect[3] and
                dino_rect[3] > obs_rect[1]):
                self.dino.is_crashed = True  # 设置恐龙碰撞状态
                return True
        return False

    def update_object(self):
        current_time = time.time()

        # 如果游戏结束且已经过去5秒，重新开始游戏
        if self.game_over:
            if current_time - self.game_over_time >= 5:
                self.reset_game()
            return

        self.frame_count += 1

        if current_time - self.last_score_update >= 0.1:
            self.score += 1
            self.last_score_update = current_time

        self.dino.update()
        self.spawn_obstacle()
        self.spawn_cloud()

        if not self.dino.is_crashed:
            if self.player == "AI":
                self.ai_decision()

        # 更新障碍物
        self.obstacles = [obs for obs in self.obstacles if not obs.update()]

        # 更新云朵
        if self.clouds is not None:
            self.clouds = [cloud for cloud in self.clouds if not cloud.update()]

        # 检查碰撞
        if self.check_collision():
            self.game_over = True
            self.game_over_time = current_time  # 记录游戏结束时间

    def draw_game(self):
        draw = self.canvas
        draw.rectangle((0, 0, WIDTH, self.height), fill=0)
        
        # 绘制地面
        draw.line((0, self.ground_y, WIDTH, self.ground_y), fill=255)
        
        # 绘制云朵
        if self.clouds is not None:
            for cloud in self.clouds:
                cloud.draw(draw)
        
        # 绘制恐龙
        self.dino.draw(draw)
        
        # 绘制障碍物
        for obstacle in self.obstacles:
            obstacle.draw(draw)
        
        if self.player != "AI":
            # 绘制分数（右对齐）
            score_text = str(self.score)
            score_bbox = draw.textbbox((0, 0), score_text, font=self.font8)
            score_width = score_bbox[2] - score_bbox[0]
            draw.text((WIDTH - score_width - 4, 2), score_text, fill=255, font=self.font8)
        
        if self.player == "AI":
            # 计算 GAME OVER 文本的边界框
            game_over_text = "press to start"
            text_bbox = draw.textbbox((0, 0), game_over_text, font=self.font8)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            # 绘制黑色文本
            text_x = WIDTH//2 - text_width//2+8
            text_y = self.height//2 - text_height//2-4
            draw.text((text_x, text_y), game_over_text, fill=255, font=self.font8)
            
        if self.game_over:
            # 计算 GAME OVER 文本的边界框
            game_over_text = "GAME OVER"
            text_bbox = draw.textbbox((0, 0), game_over_text, font=self.font8)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            # 绘制白色背景框（比文本稍大一些）
            padding = 4
            box_left = WIDTH//2 - text_width//2 - padding + 4
            box_top = self.height//2 - text_height//2 - padding - 4
            box_right = WIDTH//2 + text_width//2 + padding + 2
            box_bottom = self.height//2 + text_height//2 + padding - 8
            draw.rectangle((box_left, box_top, box_right, box_bottom), fill=0)
            
            # 绘制黑色文本
            text_x = WIDTH//2 - text_width//2 + 4
            text_y = self.height//2 - text_height//2 - 8
            draw.text((text_x, text_y), game_over_text, fill=255, font=self.font8)
            
            # 显示重启倒计时
            remaining = 5 - int(time.time() - self.game_over_time)
            if remaining > 0:
                draw.rectangle((WIDTH//2-1, self.height//2+2, WIDTH//2+10, self.height//2+10), fill=0)
                draw.text((WIDTH//2+1, self.height//2), f"{remaining}s", fill=255, font=self.font8)
                
    def render(self):
        self.update_object()
        self.draw_game()

    def key_callback(self, evt):
        # 获取全局功能按键
        key_select = self.keymap.action_select  # 跳跃/开始游戏
        key_cancel = self.keymap.action_cancel  # 跳跃/开始游戏

        if evt.value == 1:  # key down
            # select 或 cancel 键都可以跳跃/开始游戏
            if self.keymap.match(key_select) or self.keymap.match(key_cancel):
                if self.player != "You" or self.game_over:
                    self.reset_game("You")
                elif self.player == "You":
                    self.dino.jump()

    def set_active(self, active):
        super().set_active(active)
        if active:
            self.reset_game()
            self.manager.key_listener.on(self.key_callback)
        else:
            self.manager.key_listener.off(self.key_callback)
