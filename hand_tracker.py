import cv2
import mediapipe as mp

class HandTracker:
    """OpenCV와 MediaPipe를 래핑하여 손 추적을 담당하는 클래스"""
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
        """이미지에서 손을 찾아 랜드마크를 그립니다."""
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        self.results = self.hands.process(image_rgb)
        
        if self.results.multi_hand_landmarks and draw:
            for hand_landmarks in self.results.multi_hand_landmarks:
                self.mp_drawing.draw_landmarks(
                    image, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
        return image

    def get_landmarks(self):
        """탐지된 손의 랜드마크 리스트를 반환합니다."""
        if self.results and self.results.multi_hand_landmarks:
            # 첫 번째 손의 랜드마크만 반환
            return self.results.multi_hand_landmarks[0].landmark
        return None