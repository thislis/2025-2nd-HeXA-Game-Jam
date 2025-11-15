# main.py
# 이 파일의 내용을 아래 코드로 전체 교체하세요.

import pygame, cv2, time, json, random, subprocess, sys, numpy as np
from hand_tracker import HandTracker
from pose_recognition import PoseComparator
from note_system import NoteController
from judgement_engine import JudgementEngine

# --- 상수 정의 ---
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
SETUP_WEBCAM_WIDTH, SETUP_WEBCAM_HEIGHT = 320, 180 
JUDGEMENT_LINE_Y = 500; NOTE_SPEED = 300; NOTE_RADIUS = 30
SWIPE_PARAMS = {'distance': 150, 'tolerance': 120, 'grace_period': 0.25} 
NOTE_COLOR_MAP = {"DEFAULT": (200, 200, 200), "GRAB": (255, 100, 100), "PICK": (100, 255, 100), "FIST": (255, 100, 100), "OPEN": (100, 255, 100), "V": (100, 100, 255)}
JUDGEMENT_THRESHOLDS = {'PERFECT': 20, 'GREAT': 45} 

# --- UI 클래스 ---
class Button:
    def __init__(self, rect, callback, is_enabled=True, text=""):
        self.rect = pygame.Rect(rect); self.callback = callback; self.is_hovered = False; self.is_enabled = is_enabled
        self.text = text; self.font = None # 폰트는 Game 클래스에서 설정
    def handle_event(self, event):
        if not self.is_enabled: return
        if event.type == pygame.MOUSEMOTION: self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.is_hovered: self.callback()
    def draw(self, surface):
        color = (255, 255, 0) if self.is_enabled and self.is_hovered else (255, 255, 255)
        pygame.draw.rect(surface, color, self.rect, 2, border_radius=5)
        if self.text and self.font:
            text_surf = self.font.render(self.text, True, color)
            surface.blit(text_surf, text_surf.get_rect(center=self.rect.center))

# --- 포즈 설정 관리 클래스 (단순화) ---
class PoseSetupManager:
    def __init__(self):
        self.poses_to_setup = ["DEFAULT", "GRAB", "PICK"]; self.reset()

    def get_current_target(self): return self.poses_to_setup[self.current_step] if not self.is_complete else None
    
    def capture_and_advance(self, live_landmarks, pose_comparator):
        if self.is_complete or live_landmarks is None: return
        
        target_pose_name = self.get_current_target()
        normalized_landmarks = pose_comparator._normalize_landmarks(live_landmarks)
        if normalized_landmarks is not None:
            self.saved_poses[target_pose_name] = normalized_landmarks.tolist()
            print(f"Pose '{target_pose_name}' captured.")
            self.current_step += 1
            if self.current_step >= len(self.poses_to_setup): self.is_complete = True
    
    def get_instruction(self):
        if self.is_complete: return "모든 포즈가 설정되었습니다! '완료'를 누르세요."
        target = self.get_current_target()
        if target == "DEFAULT": return "기본 자세를 취하고 '저장'을 누르세요."
        if target == "GRAB": return "잡기 자세를 취하고 '저장'을 누르세요."
        if target == "PICK": return "집기 자세를 취하고 '완료'를 누르세요."
        return ""
    
    def reset(self):
        self.current_step = 0; self.saved_poses = {}; self.is_complete = False

class Game:
    def __init__(self):
        pygame.init(); self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT)); pygame.display.set_caption("Echo Shaper")
        self.clock = pygame.time.Clock(); self.font = pygame.font.Font(None, 72); self.medium_font = pygame.font.Font(None, 48); self.small_font = pygame.font.Font(None, 32)
        try: self.korean_font = pygame.font.Font("NanumGothic.ttf", 22); self.korean_font_btn = pygame.font.Font("NanumGothic.ttf", 24)
        except: self.korean_font = self.korean_font_btn = self.small_font

        self.game_state = "LOADING"; self.loading_timer = 2.0; self.credits_timer = 0
        self.loading_background = self._load_image('loading.png'); self.menu_background = self._load_image('main_menu.png'); self.setup_background = self._load_image('setting.png')
        self.menu_buttons = [Button((295, 308, 210, 50), self.start_game), Button((295, 373, 210, 50), self.go_to_pose_setup), Button((295, 438, 210, 50), self.show_credits), Button((295, 503, 210, 50), self.quit_game)]
        self.setup_capture_button = Button((550, 480, 155, 50), self.capture_pose)
        self.setup_capture_button.font = self.korean_font_btn

        self.cap = cv2.VideoCapture(0); self.hand_tracker = HandTracker(); self.pose_comparator = PoseComparator('poses.json'); self.note_controller = NoteController('level1.json', speed=NOTE_SPEED); self.judgement_engine = JudgementEngine(JUDGEMENT_LINE_Y, JUDGEMENT_THRESHOLDS, NOTE_SPEED, SWIPE_PARAMS, NOTE_RADIUS); self.pose_setup_manager = PoseSetupManager()
        self.start_time = 0; self.game_time = 0; self.delta_time = 0; self.score = 0; self.combo = 0; self.final_score = 0; self.current_pose = "UNKNOWN"; self.hand_pos = None; self.last_judgement = ""; self.judgement_display_timer = 0; self.annotated_frame = None

    def _load_image(self, path):
        try: img = pygame.image.load(path).convert(); return pygame.transform.scale(img, (SCREEN_WIDTH, SCREEN_HEIGHT))
        except pygame.error as e: print(f"Cannot load image '{path}': {e}"); return None
    
    # <<< 핵심 변경: '저장/완료' 버튼을 눌렀을 때의 로직
    def capture_pose(self):
        landmarks = self.hand_tracker.get_landmarks()
        self.pose_setup_manager.capture_and_advance(landmarks, self.pose_comparator)
        
        # 마지막 포즈까지 완료되었다면
        if self.pose_setup_manager.is_complete:
            # 1. 파일에 저장
            with open('poses.json', 'w') as f: json.dump(self.pose_setup_manager.saved_poses, f, indent=4)
            print("New poses saved to poses.json!")
            # 2. 포즈 인식기 다시 로드
            self.pose_comparator = PoseComparator('poses.json')
            # 3. 1초 로딩 후 메뉴로 복귀
            self.game_state = "LOADING"
            self.loading_timer = 1.0

    def go_to_pose_setup(self): self.pose_setup_manager.reset(); self.game_state = "POSE_SETUP"
    def start_game(self): self.reset_game(); self.game_state = "PLAYING"
    def show_credits(self): self.game_state = "CREDITS"; self.credits_timer = 5.0
    def quit_game(self): pygame.event.post(pygame.event.Event(pygame.QUIT))

    def run(self):
        is_running = True
        while is_running:
            self.delta_time = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT: is_running = False
                if self.game_state == "MENU":
                    for button in self.menu_buttons: button.handle_event(event)
                elif self.game_state == "POSE_SETUP": self.setup_capture_button.handle_event(event)
                elif self.game_state == "RESULTS":
                    if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN: self.game_state = "MENU"
            
            if self.game_state == "LOADING": self.update_loading(); self.draw_loading()
            elif self.game_state == "PLAYING": self.update_playing(); self.draw_playing()
            elif self.game_state == "MENU": self.draw_menu()
            elif self.game_state == "RESULTS": self.draw_results()
            elif self.game_state == "CREDITS": self.update_credits(); self.draw_credits()
            elif self.game_state == "POSE_SETUP": self.update_pose_setup(); self.draw_pose_setup()
            
            pygame.display.flip()
        self.quit()

    def update_pose_setup(self):
        frame = self._get_webcam_frame(flip=False);
        if frame is None: return
        self.annotated_frame = self.hand_tracker.find_hands(frame.copy())
        # 버튼 텍스트 동적 변경
        self.setup_capture_button.text = "완료" if self.pose_setup_manager.current_step == len(self.pose_setup_manager.poses_to_setup) - 1 else "저장"

    def draw_pose_setup(self):
        if self.setup_background: self.screen.blit(self.setup_background, (0, 0))
        else: self.screen.fill((20, 20, 30))
        if self.annotated_frame is not None:
            frame_rgb = cv2.cvtColor(self.annotated_frame, cv2.COLOR_BGR2RGB)
            frame_pygame = pygame.image.frombuffer(frame_rgb.tobytes(), self.annotated_frame.shape[1::-1], "RGB")
            frame_pygame = pygame.transform.scale(frame_pygame, (SETUP_WEBCAM_WIDTH, SETUP_WEBCAM_HEIGHT))
            self.screen.blit(frame_pygame, (115, 245))
        
        instruction_text = self.korean_font.render(self.pose_setup_manager.get_instruction(), True, (220, 220, 220))
        self.screen.blit(instruction_text, (105, 500))
        self.setup_capture_button.draw(self.screen)

    def update_loading(self):
        self.loading_timer -= self.delta_time
        if self.loading_timer <= 0: self.game_state = "MENU"
    def draw_loading(self):
        if self.loading_background: self.screen.blit(self.loading_background, (0, 0))
        else: self.screen.fill((0, 0, 0)); loading_text = self.font.render("Loading...", True, (255, 255, 255)); self.screen.blit(loading_text, loading_text.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2)))
    
    # 나머지 모든 메소드는 이전 버전과 거의 동일
    def draw_menu(self):
        if self.menu_background: self.screen.blit(self.menu_background, (0, 0))
        else: self.screen.fill((20, 20, 30))
        for button in self.menu_buttons: button.draw(self.screen)
    def update_credits(self):
        self.credits_timer -= self.delta_time
        if self.credits_timer <= 0: self.game_state = "MENU"
    def draw_credits(self):
        self.screen.fill((0, 0, 0)); credits_text = self.font.render("MGGA", True, (255, 255, 255)); self.screen.blit(credits_text, credits_text.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2)))
    def update_playing(self):
        self.game_time = time.time() - self.start_time; frame = self._get_webcam_frame()
        if frame is None: return
        self.annotated_frame = self.hand_tracker.find_hands(frame.copy())
        self.current_pose, _ = self.pose_comparator.match_pose(self.hand_tracker.get_landmarks())
        self.hand_pos = self.hand_tracker.get_hand_position(self.annotated_frame.shape[1], self.annotated_frame.shape[0])
        if self.hand_pos:
            webcam_x_offset = (SCREEN_WIDTH - self.annotated_frame.shape[1]) // 2; self.hand_pos = (self.hand_pos[0] + webcam_x_offset, self.hand_pos[1] + 20)
        self.note_controller.update(self.game_time, self.delta_time)
        judgements = self.judgement_engine.check_judgements(self.note_controller.notes, self.current_pose, self.hand_pos, self.game_time, self.delta_time)
        notes_to_remove = []
        for j in judgements:
            self.process_judgement(j); note, judgement_type = j['note'], j['judgement']
            if note.note_type == 'swipe' and judgement_type in ['PERFECT', 'GREAT']: note.y_pos = JUDGEMENT_LINE_Y
            if note.note_type == 'tap' or judgement_type in ['MISS', 'HOLD_BREAK', 'HOLD_SUCCESS', 'SWIPE_BREAK', 'SWIPE_SUCCESS']: notes_to_remove.append(note)
        if notes_to_remove: self.note_controller.notes = [n for n in self.note_controller.notes if n not in notes_to_remove]
        if self.note_controller.spawn_index == len(self.note_controller.beatmap) and not self.note_controller.notes:
            self.final_score = self.score; self.game_state = "RESULTS"
    def process_judgement(self, judgement_info):
        judgement = judgement_info['judgement']
        if judgement in ["PERFECT", "GREAT"]: self.combo += 1; self.score += 100 if judgement == "PERFECT" else 50
        elif judgement in ["MISS", "HOLD_BREAK", "SWIPE_BREAK"]: self.combo = 0
        elif judgement == "HOLD_SUCCESS": self.combo += 1; self.score += 200
        elif judgement == "SWIPE_SUCCESS": self.combo += 1; self.score += 300
        if judgement_info['note'].is_holding or judgement_info['note'].is_swiping: self.score += 2
        if judgement not in ['HOLD_SUCCESS', 'SWIPE_SUCCESS']: self.last_judgement = judgement; self.judgement_display_timer = 1.0
    def draw_playing(self):
        self.screen.fill((20, 20, 30));
        if self.annotated_frame is not None:
            frame_rgb = cv2.cvtColor(self.annotated_frame, cv2.COLOR_BGR2RGB)
            frame_pygame = pygame.image.frombuffer(frame_rgb.tobytes(), self.annotated_frame.shape[1::-1], "RGB")
            self.screen.blit(frame_pygame, ((SCREEN_WIDTH - self.annotated_frame.shape[1]) // 2, 20))
        pygame.draw.line(self.screen, (255, 255, 0), (0, JUDGEMENT_LINE_Y), (SCREEN_WIDTH, JUDGEMENT_LINE_Y), 3)
        for note in self.note_controller.notes: self._draw_note(note)
        self._draw_hud()
    def _draw_note(self, note):
        color = NOTE_COLOR_MAP.get(note.target_pose, NOTE_COLOR_MAP["DEFAULT"]); note_x_pos = SCREEN_WIDTH // 2
        if note.note_type == 'tap': pygame.draw.circle(self.screen, color, (note_x_pos, int(note.y_pos)), NOTE_RADIUS)
        elif note.note_type == 'hold':
            hold_length = note.duration * NOTE_SPEED; body_color = (80, 80, 80) if note.is_failed else ((255, 255, 255) if note.is_holding else color)
            pygame.draw.rect(self.screen, body_color, (note_x_pos - 25, int(note.y_pos - hold_length), 50, hold_length), border_radius=10)
            pygame.draw.circle(self.screen, color, (note_x_pos, int(note.y_pos)), NOTE_RADIUS)
        elif note.note_type == 'swipe':
            y_draw_pos = int(note.y_pos); start_pos = (note_x_pos, y_draw_pos)
            end_x = start_pos[0] + SWIPE_PARAMS['distance'] if note.direction == "RIGHT" else start_pos[0] - SWIPE_PARAMS['distance']
            end_pos = (end_x, y_draw_pos)
            if note.is_swiping:
                progress = ((self.game_time - (note.spawn_time + ((JUDGEMENT_LINE_Y) / NOTE_SPEED))) / note.duration) * 1.5; progress = max(0, min(1, progress))
                interp_x = start_pos[0] + (end_pos[0] - start_pos[0]) * progress; pygame.draw.circle(self.screen, (255,255,0,100), (interp_x, start_pos[1]), 15)
            line_color = (255,255,255) if note.is_swiping else color; pygame.draw.line(self.screen, line_color, start_pos, end_pos, 10)
            pygame.draw.circle(self.screen, color, start_pos, NOTE_RADIUS); pygame.draw.circle(self.screen, color, end_pos, NOTE_RADIUS, 5)
        pose_text_y = int(note.y_pos); pose_text = self.small_font.render(note.target_pose, True, (0,0,0)); self.screen.blit(pose_text, pose_text.get_rect(center=(note_x_pos, pose_text_y)))
    def _draw_hud(self):
        if self.hand_pos: pygame.draw.circle(self.screen, (0, 255, 255), self.hand_pos, 10)
        score_text = self.medium_font.render(f"Score: {self.score}", True, (255, 255, 255)); self.screen.blit(score_text, (10, 10))
        if self.combo > 2:
            combo_text = self.medium_font.render(f"{self.combo} Combo", True, (255, 200, 0)); self.screen.blit(combo_text, (SCREEN_WIDTH // 2 - combo_text.get_width() // 2, 150))
        pose_text = self.small_font.render(f"Pose: {self.current_pose}", True, (255, 255, 255)); self.screen.blit(pose_text, (SCREEN_WIDTH - pose_text.get_width() - 10, 10))
        if self.judgement_display_timer > 0:
            self.judgement_display_timer -= self.delta_time
            judgement_color = {"PERFECT": (0,255,255), "GREAT": (0,255,0), "MISS": (255,0,0), "HOLD_BREAK": (255,0,0), "SWIPE_BREAK": (255,0,0)}
            text = self.font.render(self.last_judgement, True, judgement_color.get(self.last_judgement, (255,255,255))); self.screen.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, 300)))
    def reset_game(self):
        self.score = 0; self.combo = 0; self.last_judgement = ""; self.judgement_display_timer = 0
        self.note_controller.reset(); self.start_time = time.time()
    def draw_results(self):
        self.screen.fill((20, 20, 30)); title = self.font.render("RESULTS", True, (255, 200, 0)); score = self.medium_font.render(f"Final Score: {self.final_score}", True, (255, 255, 255)); prompt = self.small_font.render("Press any key or click to return to Menu", True, (200, 200, 200))
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 100))); self.screen.blit(score, score.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))); self.screen.blit(prompt, prompt.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 100)))
    def _get_webcam_frame(self, flip=True):
        success, frame = self.cap.read();
        if not success: return None
        return cv2.flip(frame, 1) if flip else frame
    def quit(self): self.cap.release(); pygame.quit()

if __name__ == '__main__':
    def generate_test_beatmap(poses):
        notes = []; current_time = 2.0
        available_game_poses = [p for p in poses if p in ["DEFAULT", "GRAB", "PICK"]]
        if not available_game_poses: available_game_poses = ["DEFAULT"]
        for _ in range(12):
            note_type = random.choice(['tap', 'hold', 'swipe']); pose = random.choice(available_game_poses)
            if note_type == 'tap': notes.append({"time": current_time, "pose": pose, "type": "tap"}); current_time += random.uniform(0.8, 1.2)
            elif note_type == 'hold':
                duration = random.uniform(1.0, 2.0)
                notes.append({"time": current_time, "pose": pose, "type": "hold", "duration": duration})
                current_time += duration + random.uniform(0.5, 1.0)
            elif note_type == 'swipe':
                duration = random.uniform(1.2, 2.25); direction = random.choice(["LEFT", "RIGHT"])
                notes.append({"time": current_time, "pose": pose, "type": "swipe", "duration": duration, "direction": direction})
                current_time += duration + random.uniform(0.5, 1.0)
        return {"song": "dynamic_test_beatmap", "bpm": 120, "notes": notes}
    available_poses = []
    try:
        with open('poses.json', 'r') as f: available_poses = list(json.load(f).keys())
    except FileNotFoundError: pass
    if not available_poses: available_poses = ["DEFAULT", "GRAB", "PICK"]
    with open('level1.json', 'w') as f: json.dump(generate_test_beatmap(available_poses), f, indent=4)
    game = Game(); game.run()