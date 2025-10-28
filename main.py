import pygame
import cv2
import time
import json
from hand_tracker import HandTracker
from pose_recognition import PoseComparator
from note_system import NoteController
from judgement_engine import JudgementEngine

# --- 상수 정의 ---
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
WEBCAM_WIDTH, WEBCAM_HEIGHT = 640, 480
JUDGEMENT_LINE_Y = 500
NOTE_COLOR_MAP = {
    "FIST": (255, 0, 0), "OPEN": (0, 255, 0), "V": (0, 0, 255), "DEFAULT": (200, 200, 200)
}
JUDGEMENT_THRESHOLDS = {'PERFECT': 40, 'GREAT': 80}

class Game:
    """게임의 메인 루프와 모든 시스템을 관리하는 클래스"""
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Echo Shaper - Prototype")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 32)
        
        self.is_running = True
        self.game_time = 0

        # 시스템 초기화
        self.cap = cv2.VideoCapture(0)
        self.hand_tracker = HandTracker()
        self.pose_comparator = PoseComparator('poses.json')
        self.note_controller = NoteController('level1.json', speed=350)
        self.judgement_engine = JudgementEngine(JUDGEMENT_LINE_Y, JUDGEMENT_THRESHOLDS)

        # 게임 상태 변수
        self.score = 0
        self.combo = 0
        self.current_pose = "UNKNOWN"
        self.last_judgement = ""
        self.judgement_display_timer = 0

    def run(self):
        """메인 게임 루프"""
        start_time = time.time()
        while self.is_running:
            delta_time = self.clock.tick(60) / 1000.0
            self.game_time = time.time() - start_time

            # 1. 이벤트 처리
            self.handle_events()

            # 2. 데이터 업데이트
            frame = self.get_webcam_frame()
            annotated_frame = self.hand_tracker.find_hands(frame.copy())
            landmarks = self.hand_tracker.get_landmarks()
            self.current_pose, _ = self.pose_comparator.match_pose(landmarks)
            
            self.note_controller.update(self.game_time, delta_time)

            # 3. 판정 로직
            judgements = self.judgement_engine.check_judgements(
                self.note_controller.notes, self.current_pose
            )
            for j in judgements:
                self.process_judgement(j['judgement'])
                self.note_controller.notes.remove(j['note'])

            # 4. 렌더링
            self.draw_all(annotated_frame)
        
        self.quit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_running = False

    def get_webcam_frame(self):
        success, frame = self.cap.read()
        if not success:
            # 웹캠이 없으면 검은 화면으로 대체
            return pygame.Surface((WEBCAM_WIDTH, WEBCAM_HEIGHT)).fill((0,0,0))
        frame = cv2.flip(frame, 1)
        return frame

    def process_judgement(self, judgement):
        self.last_judgement = judgement
        self.judgement_display_timer = 1.0 # 1초간 표시

        if judgement == "PERFECT":
            self.score += 100
            self.combo += 1
        elif judgement == "GREAT":
            self.score += 50
            self.combo += 1
        elif judgement == "MISS":
            self.combo = 0

    def draw_all(self, frame):
        self.screen.fill((20, 20, 30)) # 다크 블루 배경

        # 웹캠 화면 렌더링
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_pygame = pygame.image.frombuffer(frame_rgb.tobytes(), frame.shape[1::-1], "RGB")
        # 화면 중앙에 맞춤
        webcam_x = (SCREEN_WIDTH - WEBCAM_WIDTH) // 2
        self.screen.blit(frame_pygame, (webcam_x, 20))

        # 판정선 렌더링
        pygame.draw.line(self.screen, (255, 255, 0), (0, JUDGEMENT_LINE_Y), (SCREEN_WIDTH, JUDGEMENT_LINE_Y), 3)

        # 노트 렌더링
        for note in self.note_controller.notes:
            color = NOTE_COLOR_MAP.get(note.target_pose, NOTE_COLOR_MAP["DEFAULT"])
            # 노트 위치를 웹캠 화면 중앙 기준으로 조정
            note_x_pos = SCREEN_WIDTH // 2
            pygame.draw.circle(self.screen, color, (note_x_pos, int(note.y_pos)), 30)
            pose_text = self.small_font.render(note.target_pose, True, (255, 255, 255))
            text_rect = pose_text.get_rect(center=(note_x_pos, int(note.y_pos)))
            self.screen.blit(pose_text, text_rect)

        # HUD 렌더링
        self.draw_hud()

        pygame.display.flip()
        
    def draw_hud(self):
        # 점수
        score_text = self.font.render(f"Score: {self.score}", True, (255, 255, 255))
        self.screen.blit(score_text, (10, 10))
        
        # 콤보
        if self.combo > 2:
            combo_text = self.font.render(f"{self.combo} Combo", True, (255, 200, 0))
            self.screen.blit(combo_text, (SCREEN_WIDTH // 2 - combo_text.get_width() // 2, 150))
            
        # 현재 인식된 포즈
        pose_text = self.small_font.render(f"Pose: {self.current_pose}", True, (255, 255, 255))
        self.screen.blit(pose_text, (SCREEN_WIDTH - pose_text.get_width() - 10, 10))

        # FPS
        fps = self.clock.get_fps()
        fps_text = self.small_font.render(f"FPS: {int(fps)}", True, (255, 255, 255))
        self.screen.blit(fps_text, (SCREEN_WIDTH - fps_text.get_width() - 10, 40))

        # 판정 결과
        if self.judgement_display_timer > 0:
            self.judgement_display_timer -= self.clock.get_time() / 1000.0
            judgement_color = {"PERFECT": (0, 255, 255), "GREAT": (0, 255, 0), "MISS": (255, 0, 0)}
            text = self.font.render(self.last_judgement, True, judgement_color.get(self.last_judgement, (255,255,255)))
            text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, 300))
            self.screen.blit(text, text_rect)


    def quit(self):
        """게임 종료 처리"""
        print("--- Game Over ---")
        print(f"Final Score: {self.score}")
        self.cap.release()
        pygame.quit()


if __name__ == '__main__':
    # 비트맵 파일 생성
    beatmap_data = {
        "song": "test_song",
        "bpm": 120,
        "notes": [
            {"time": 2.0, "pose": "FIST"},
            {"time": 3.0, "pose": "OPEN"},
            {"time": 4.0, "pose": "V"},
            {"time": 5.0, "pose": "FIST"},
            {"time": 5.5, "pose": "OPEN"},
            {"time": 6.0, "pose": "V"},
            {"time": 7.0, "pose": "OPEN"},
            {"time": 7.25, "pose": "FIST"},
            {"time": 7.5, "pose": "OPEN"},
            {"time": 7.75, "pose": "FIST"},
            {"time": 9.0, "pose": "V"}
        ]
    }
    with open('level1.json', 'w') as f:
        json.dump(beatmap_data, f)

    game = Game()
    game.run()