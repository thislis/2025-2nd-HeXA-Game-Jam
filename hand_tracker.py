# hand_tracker.py
# 기존 클래스에 get_hand_position 메소드를 추가합니다.
import cv2
import mediapipe as mp

class HandTracker:
    def __init__(self, max_hands=1, detection_con=0.7, track_con=0.7):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=max_hands,
            min_detection_confidence=detection_con,
            min_tracking_confidence=track_con
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.results = None

    def find_hands(self, image, draw=True):
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        self.results = self.hands.process(image_rgb)
        
        if self.results.multi_hand_landmarks and draw:
            for hand_landmarks in self.results.multi_hand_landmarks:
                self.mp_drawing.draw_landmarks(
                    image, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
        return image

    def get_landmarks(self):
        if self.results and self.results.multi_hand_landmarks:
            return self.results.multi_hand_landmarks[0].landmark
        return None

    def get_hand_position(self, image_width, image_height):
        """손목(landmark 0)의 화면 좌표 (x, y)를 반환합니다."""
        landmarks = self.get_landmarks()
        if landmarks:
            wrist = landmarks[0]
            x, y = int(wrist.x * image_width), int(wrist.y * image_height)
            return x, y
        return None