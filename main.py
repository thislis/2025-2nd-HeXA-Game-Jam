# main.py
# 이 파일의 내용을 아래 코드로 전체 교체하세요.

import pygame
import cv2
import time
import json
import random
from hand_tracker import HandTracker
from pose_recognition import PoseComparator
from note_system import NoteController
from judgement_engine import JudgementEngine

# --- 상수 정의 ---
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
WEBCAM_WIDTH, WEBCAM_HEIGHT = 640, 480
JUDGEMENT_LINE_Y = 500
NOTE_SPEED = 350
NOTE_COLOR_MAP = {
    "FIST": (255, 100, 100), "OPEN": (100, 255, 100), "V": (100, 100, 255), "DEFAULT": (200, 200, 200)
}
JUDGEMENT_THRESHOLDS = {'PERFECT': 40, 'GREAT': 80}


class Game:
    # __init__ 등 다른 부분은 이전과 동일하게 유지
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Echo Shaper - Prototype v4 (Corrected Holds)")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 72)
        self.medium_font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 32)
        
        self.game_state = "MENU"
        self.start_time = 0
        self.game_time = 0
        self.delta_time = 0

        self.cap = cv2.VideoCapture(0)
        self.hand_tracker = HandTracker()
        self.pose_comparator = PoseComparator('poses.json')
        self.note_controller = NoteController('level1.json', speed=NOTE_SPEED)
        self.judgement_engine = JudgementEngine(JUDGEMENT_LINE_Y, JUDGEMENT_THRESHOLDS, NOTE_SPEED)

        self.score = 0
        self.combo = 0
        self.current_pose = "UNKNOWN"
        self.last_judgement = ""
        self.judgement_display_timer = 0
        self.final_score = 0
        self.annotated_frame = None

    def run(self):
        is_running = True
        while is_running:
            self.delta_time = self.clock.tick(60) / 1000.0
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    is_running = False
                self.handle_input(event)

            if self.game_state == "MENU":
                self.draw_menu()
            elif self.game_state == "PLAYING":
                self.update_playing()
                self.draw_playing()
            elif self.game_state == "RESULTS":
                self.draw_results()
            
            pygame.display.flip()
        self.quit()

    def update_playing(self):
        self.game_time = time.time() - self.start_time

        # 1. 입력 및 상태 업데이트
        frame = self._get_webcam_frame()
        self.annotated_frame = self.hand_tracker.find_hands(frame.copy())
        landmarks = self.hand_tracker.get_landmarks()
        self.current_pose, _ = self.pose_comparator.match_pose(landmarks)
        self.note_controller.update(self.game_time, self.delta_time)

        # 2. 판정 실행
        judgements = self.judgement_engine.check_judgements(
            self.note_controller.notes, self.current_pose
        )

        # 3. 판정 결과 처리 (점수, 콤보, 상태 변경)
        notes_to_remove = []
        for j in judgements:
            self.process_judgement(j)
            
            # 4. 노트 제거 조건 판별 (매우 중요!)
            judgement_type = j['judgement']
            note = j['note']
            
            # Tap 노트는 판정이 나면 무조건 제거
            if note.note_type == 'tap':
                notes_to_remove.append(note)
            # Hold 노트는 최종 판정(성공, 실패, 미스) 시에만 제거
            elif note.note_type == 'hold':
                if judgement_type in ['MISS', 'HOLD_BREAK', 'HOLD_SUCCESS']:
                    notes_to_remove.append(note)

        # 5. 실제 노트 리스트에서 제거
        if notes_to_remove:
            self.note_controller.notes = [n for n in self.note_controller.notes if n not in notes_to_remove]
        
        # 6. 게임 종료 조건 확인
        if self.note_controller.spawn_index == len(self.note_controller.beatmap) and not self.note_controller.notes:
            self.final_score = self.score
            self.game_state = "RESULTS"

    def process_judgement(self, judgement_info):
        judgement = judgement_info['judgement']
        note = judgement_info['note']

        # 점수 및 콤보 처리
        if judgement in ["PERFECT", "GREAT"]:
            self.combo += 1
            self.score += 100 if judgement == "PERFECT" else 50
        elif judgement in ["MISS", "HOLD_BREAK"]:
            self.combo = 0
        elif judgement == "HOLD_SUCCESS":
            self.combo += 1
            self.score += 200 # 홀드 성공 보너스
        
        # 홀드 유지 점수 (성공적으로 홀드 중일 때만)
        if note.is_holding:
            self.score += 2

        # 판정 텍스트 표시
        if judgement != 'HOLD_SUCCESS': # 성공 판정은 조용히 처리
            self.last_judgement = judgement
            self.judgement_display_timer = 1.0

    # `draw_playing` 및 기타 메소드들은 이전과 동일하게 유지됩니다.
    # ... (이전 답변의 main.py 코드와 동일)
    # --- 나머지 Game 클래스 메소드들은 이전과 동일 ---
    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if self.game_state == "MENU":
                self.start_game()
            elif self.game_state == "RESULTS":
                self.game_state = "MENU"
    def start_game(self):
        self.reset_game()
        self.game_state = "PLAYING"
    def reset_game(self):
        self.score = 0
        self.combo = 0
        self.last_judgement = ""
        self.judgement_display_timer = 0
        self.note_controller.reset()
        self.start_time = time.time()
    def draw_menu(self):
        self.screen.fill((20, 20, 30))
        title_text = self.font.render("Echo Shaper", True, (0, 255, 255))
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
        prompt_text = self.medium_font.render("Press any key to start", True, (255, 255, 255))
        prompt_rect = prompt_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50))
        self.screen.blit(title_text, title_rect)
        self.screen.blit(prompt_text, prompt_rect)
    def draw_playing(self):
        self.screen.fill((20, 20, 30))
        if self.annotated_frame is not None:
            frame_rgb = cv2.cvtColor(self.annotated_frame, cv2.COLOR_BGR2RGB)
            frame_pygame = pygame.image.frombuffer(frame_rgb.tobytes(), self.annotated_frame.shape[1::-1], "RGB")
            webcam_x = (SCREEN_WIDTH - WEBCAM_WIDTH) // 2
            self.screen.blit(frame_pygame, (webcam_x, 20))
        pygame.draw.line(self.screen, (255, 255, 0), (0, JUDGEMENT_LINE_Y), (SCREEN_WIDTH, JUDGEMENT_LINE_Y), 3)
        for note in self.note_controller.notes:
            self._draw_note(note)
        self._draw_hud()
    def draw_results(self):
        self.screen.fill((20, 20, 30))
        title_text = self.font.render("RESULTS", True, (255, 200, 0))
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100))
        score_text = self.medium_font.render(f"Final Score: {self.final_score}", True, (255, 255, 255))
        score_rect = score_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        prompt_text = self.small_font.render("Press any key to return to Menu", True, (200, 200, 200))
        prompt_rect = prompt_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100))
        self.screen.blit(title_text, title_rect)
        self.screen.blit(score_text, score_rect)
        self.screen.blit(prompt_text, prompt_rect)
    def _get_webcam_frame(self):
        success, frame = self.cap.read()
        return cv2.flip(frame, 1) if success else pygame.Surface((WEBCAM_WIDTH, WEBCAM_HEIGHT)).fill((0,0,0))
    def _draw_note(self, note):
        color = NOTE_COLOR_MAP.get(note.target_pose, NOTE_COLOR_MAP["DEFAULT"])
        note_x_pos = SCREEN_WIDTH // 2
        if note.note_type == 'tap':
            pygame.draw.circle(self.screen, color, (note_x_pos, int(note.y_pos)), 30)
        elif note.note_type == 'hold':
            hold_length = note.duration * NOTE_SPEED
            if note.is_failed: body_color = (80, 80, 80)
            elif note.is_holding: body_color = (255, 255, 255)
            else: body_color = color
            rect = pygame.Rect(note_x_pos - 25, int(note.y_pos - hold_length), 50, hold_length)
            pygame.draw.rect(self.screen, body_color, rect, border_radius=10)
            pygame.draw.circle(self.screen, color, (note_x_pos, int(note.y_pos)), 30)
        pose_text = self.small_font.render(note.target_pose, True, (0,0,0))
        text_rect = pose_text.get_rect(center=(note_x_pos, int(note.y_pos)))
        self.screen.blit(pose_text, text_rect)
    def _draw_hud(self):
        score_text = self.medium_font.render(f"Score: {self.score}", True, (255, 255, 255))
        self.screen.blit(score_text, (10, 10))
        if self.combo > 2:
            combo_text = self.medium_font.render(f"{self.combo} Combo", True, (255, 200, 0))
            self.screen.blit(combo_text, (SCREEN_WIDTH // 2 - combo_text.get_width() // 2, 150))
        pose_text = self.small_font.render(f"Pose: {self.current_pose}", True, (255, 255, 255))
        self.screen.blit(pose_text, (SCREEN_WIDTH - pose_text.get_width() - 10, 10))
        fps = self.clock.get_fps()
        fps_text = self.small_font.render(f"FPS: {int(fps)}", True, (255, 255, 255))
        self.screen.blit(fps_text, (SCREEN_WIDTH - fps_text.get_width() - 10, 40))
        if self.judgement_display_timer > 0:
            self.judgement_display_timer -= self.delta_time
            judgement_color = {"PERFECT": (0, 255, 255), "GREAT": (0, 255, 0), "MISS": (255, 0, 0), "HOLD_BREAK": (255,0,0)}
            text = self.font.render(self.last_judgement, True, judgement_color.get(self.last_judgement, (255,255,255)))
            text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, 300))
            self.screen.blit(text, text_rect)
    def quit(self):
        self.cap.release()
        pygame.quit()

if __name__ == '__main__':
    # 비트맵 생성 로직은 이전과 동일하게 유지
    def generate_test_beatmap(poses):
        notes = []
        current_time = 2.0
        for i in range(10):
            note_type = random.choice(['tap', 'tap', 'hold'])
            pose = random.choice(poses)
            if note_type == 'tap':
                notes.append({"time": current_time, "pose": pose, "type": "tap"})
                current_time += random.uniform(0.8, 1.5)
            else:
                duration = random.uniform(1.0, 2.5)
                notes.append({"time": current_time, "pose": pose, "type": "hold", "duration": duration})
                current_time += duration + random.uniform(0.5, 1.0)
        return {"song": "dynamic_test_song_v4", "bpm": 120, "notes": notes}
    available_poses = []
    try:
        with open('poses.json', 'r') as f:
            available_poses = list(json.load(f).keys())
    except FileNotFoundError: pass
    if not available_poses: available_poses = ["FIST", "OPEN", "V"]
    beatmap_data = generate_test_beatmap(available_poses)
    with open('level1.json', 'w') as f:
        json.dump(beatmap_data, f, indent=4)
    game = Game()
    game.run()