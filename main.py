# main.py
# 이 파일의 내용을 아래 코드로 전체 교체하세요.

import pygame, cv2, time, json, random
from hand_tracker import HandTracker
from pose_recognition import PoseComparator
from note_system import NoteController
from judgement_engine import JudgementEngine

# --- 상수 정의 ---
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
WEBCAM_WIDTH, WEBCAM_HEIGHT = 640, 480
JUDGEMENT_LINE_Y = 500
NOTE_SPEED = 300
NOTE_RADIUS = 30 # <<< 노트 반지름을 상수로 정의
SWIPE_PARAMS = {'distance': 150, 'tolerance': 120, 'grace_period': 0.25} 
NOTE_COLOR_MAP = {
    "FIST": (255, 100, 100), "OPEN": (100, 255, 100), "V": (100, 100, 255), "DEFAULT": (200, 200, 200)
}
# <<< 변경된 부분: 판정 범위를 이전의 약 절반으로 대폭 축소
JUDGEMENT_THRESHOLDS = {'PERFECT': 20, 'GREAT': 45} 

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Echo Shaper - Prototype v10 (Precise Judgement)")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 72)
        self.medium_font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 32)
        
        self.game_state = "MENU"
        self.start_time = 0; self.game_time = 0; self.delta_time = 0

        self.cap = cv2.VideoCapture(0)
        self.hand_tracker = HandTracker()
        self.pose_comparator = PoseComparator('poses.json')
        self.note_controller = NoteController('level1.json', speed=NOTE_SPEED)
        # <<< 변경된 부분: JudgementEngine에 NOTE_RADIUS 전달
        self.judgement_engine = JudgementEngine(JUDGEMENT_LINE_Y, JUDGEMENT_THRESHOLDS, NOTE_SPEED, SWIPE_PARAMS, NOTE_RADIUS)

        self.score = 0; self.combo = 0; self.final_score = 0
        self.current_pose = "UNKNOWN"; self.hand_pos = None
        self.last_judgement = ""; self.judgement_display_timer = 0
        self.annotated_frame = None

    # 나머지 모든 메소드는 이전 버전과 동일합니다.
    def run(self):
        is_running = True
        while is_running:
            self.delta_time = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT: is_running = False
                self.handle_input(event)
            if self.game_state == "PLAYING": self.update_playing(); self.draw_playing()
            elif self.game_state == "MENU": self.draw_menu()
            elif self.game_state == "RESULTS": self.draw_results()
            pygame.display.flip()
        self.quit()
    def update_playing(self):
        self.game_time = time.time() - self.start_time
        frame = self._get_webcam_frame()
        self.annotated_frame = self.hand_tracker.find_hands(frame.copy())
        self.current_pose, _ = self.pose_comparator.match_pose(self.hand_tracker.get_landmarks())
        self.hand_pos = self.hand_tracker.get_hand_position(WEBCAM_WIDTH, WEBCAM_HEIGHT)
        if self.hand_pos:
            webcam_x_offset = (SCREEN_WIDTH - WEBCAM_WIDTH) // 2
            self.hand_pos = (self.hand_pos[0] + webcam_x_offset, self.hand_pos[1] + 20)
        self.note_controller.update(self.game_time, self.delta_time)
        judgements = self.judgement_engine.check_judgements(self.note_controller.notes, self.current_pose, self.hand_pos, self.game_time, self.delta_time)
        notes_to_remove = []
        for j in judgements:
            self.process_judgement(j)
            note, judgement_type = j['note'], j['judgement']
            if note.note_type == 'swipe' and judgement_type in ['PERFECT', 'GREAT']:
                note.y_pos = JUDGEMENT_LINE_Y
            if note.note_type == 'tap' or judgement_type in ['MISS', 'HOLD_BREAK', 'HOLD_SUCCESS', 'SWIPE_BREAK', 'SWIPE_SUCCESS']:
                notes_to_remove.append(note)
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
        if judgement not in ['HOLD_SUCCESS', 'SWIPE_SUCCESS']:
            self.last_judgement = judgement; self.judgement_display_timer = 1.0
    def draw_playing(self):
        self.screen.fill((20, 20, 30))
        if self.annotated_frame is not None:
            frame_rgb = cv2.cvtColor(self.annotated_frame, cv2.COLOR_BGR2RGB)
            frame_pygame = pygame.image.frombuffer(frame_rgb.tobytes(), self.annotated_frame.shape[1::-1], "RGB")
            self.screen.blit(frame_pygame, ((SCREEN_WIDTH - WEBCAM_WIDTH) // 2, 20))
        pygame.draw.line(self.screen, (255, 255, 0), (0, JUDGEMENT_LINE_Y), (SCREEN_WIDTH, JUDGEMENT_LINE_Y), 3)
        for note in self.note_controller.notes: self._draw_note(note)
        self._draw_hud()
    def _draw_note(self, note):
        color = NOTE_COLOR_MAP.get(note.target_pose, NOTE_COLOR_MAP["DEFAULT"])
        note_x_pos = SCREEN_WIDTH // 2
        if note.note_type == 'tap': pygame.draw.circle(self.screen, color, (note_x_pos, int(note.y_pos)), NOTE_RADIUS)
        elif note.note_type == 'hold':
            hold_length = note.duration * NOTE_SPEED
            body_color = (80, 80, 80) if note.is_failed else ((255, 255, 255) if note.is_holding else color)
            pygame.draw.rect(self.screen, body_color, (note_x_pos - 25, int(note.y_pos - hold_length), 50, hold_length), border_radius=10)
            pygame.draw.circle(self.screen, color, (note_x_pos, int(note.y_pos)), NOTE_RADIUS)
        elif note.note_type == 'swipe':
            y_draw_pos = int(note.y_pos)
            start_pos = (note_x_pos, y_draw_pos)
            end_x = start_pos[0] + SWIPE_PARAMS['distance'] if note.direction == "RIGHT" else start_pos[0] - SWIPE_PARAMS['distance']
            end_pos = (end_x, y_draw_pos)
            if note.is_swiping:
                progress = ((self.game_time - (note.spawn_time + ((JUDGEMENT_LINE_Y) / NOTE_SPEED))) / note.duration) * 1.5
                progress = max(0, min(1, progress))
                interp_x = start_pos[0] + (end_pos[0] - start_pos[0]) * progress
                pygame.draw.circle(self.screen, (255,255,0,100), (interp_x, start_pos[1]), 15)
            line_color = (255,255,255) if note.is_swiping else color
            pygame.draw.line(self.screen, line_color, start_pos, end_pos, 10)
            pygame.draw.circle(self.screen, color, start_pos, NOTE_RADIUS)
            pygame.draw.circle(self.screen, color, end_pos, NOTE_RADIUS, 5)
        pose_text_y = int(note.y_pos)
        pose_text = self.small_font.render(note.target_pose, True, (0,0,0))
        self.screen.blit(pose_text, pose_text.get_rect(center=(note_x_pos, pose_text_y)))
    def _draw_hud(self):
        if self.hand_pos: pygame.draw.circle(self.screen, (0, 255, 255), self.hand_pos, 10)
        score_text = self.medium_font.render(f"Score: {self.score}", True, (255, 255, 255))
        self.screen.blit(score_text, (10, 10))
        if self.combo > 2:
            combo_text = self.medium_font.render(f"{self.combo} Combo", True, (255, 200, 0))
            self.screen.blit(combo_text, (SCREEN_WIDTH // 2 - combo_text.get_width() // 2, 150))
        pose_text = self.small_font.render(f"Pose: {self.current_pose}", True, (255, 255, 255))
        self.screen.blit(pose_text, (SCREEN_WIDTH - pose_text.get_width() - 10, 10))
        if self.judgement_display_timer > 0:
            self.judgement_display_timer -= self.delta_time
            judgement_color = {"PERFECT": (0,255,255), "GREAT": (0,255,0), "MISS": (255,0,0), "HOLD_BREAK": (255,0,0), "SWIPE_BREAK": (255,0,0)}
            text = self.font.render(self.last_judgement, True, judgement_color.get(self.last_judgement, (255,255,255)))
            self.screen.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, 300)))
    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if self.game_state == "MENU": self.start_game()
            elif self.game_state == "RESULTS": self.game_state = "MENU"
    def start_game(self): self.reset_game(); self.game_state = "PLAYING"
    def reset_game(self):
        self.score = 0; self.combo = 0; self.last_judgement = ""
        self.judgement_display_timer = 0; self.note_controller.reset()
        self.start_time = time.time()
    def draw_menu(self):
        self.screen.fill((20, 20, 30))
        title = self.font.render("Echo Shaper", True, (0, 255, 255))
        prompt = self.medium_font.render("Press any key to start", True, (255, 255, 255))
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50)))
        self.screen.blit(prompt, prompt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50)))
    def draw_results(self):
        self.screen.fill((20, 20, 30))
        title = self.font.render("RESULTS", True, (255, 200, 0))
        score = self.medium_font.render(f"Final Score: {self.final_score}", True, (255, 255, 255))
        prompt = self.small_font.render("Press any key to return to Menu", True, (200, 200, 200))
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 100)))
        self.screen.blit(score, score.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2)))
        self.screen.blit(prompt, prompt.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 100)))
    def _get_webcam_frame(self):
        success, frame = self.cap.read(); return cv2.flip(frame, 1) if success else pygame.Surface((WEBCAM_WIDTH, WEBCAM_HEIGHT)).fill((0,0,0))
    def quit(self): self.cap.release(); pygame.quit()

if __name__ == '__main__':
    def generate_test_beatmap(poses):
        notes = []; current_time = 2.0
        for _ in range(12):
            note_type = random.choice(['tap', 'hold', 'swipe'])
            pose = random.choice(poses)
            if note_type == 'tap':
                notes.append({"time": current_time, "pose": pose, "type": "tap"})
                current_time += random.uniform(0.8, 1.2)
            elif note_type == 'hold':
                duration = random.uniform(1.0, 2.0)
                notes.append({"time": current_time, "pose": pose, "type": "hold", "duration": duration})
                current_time += duration + random.uniform(0.5, 1.0)
            elif note_type == 'swipe':
                duration = random.uniform(1.2, 2.25)
                direction = random.choice(["LEFT", "RIGHT"])
                notes.append({"time": current_time, "pose": pose, "type": "swipe", "duration": duration, "direction": direction})
                current_time += duration + random.uniform(0.5, 1.0)
        return {"song": "dynamic_test_song_v10", "bpm": 120, "notes": notes}
    available_poses = [];
    try:
        with open('poses.json', 'r') as f: available_poses = list(json.load(f).keys())
    except FileNotFoundError: pass
    if not available_poses: available_poses = ["FIST", "OPEN", "V"]
    with open('level1.json', 'w') as f: json.dump(generate_test_beatmap(available_poses), f, indent=4)
    game = Game(); game.run()