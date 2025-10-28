import cv2
import mediapipe as mp
import numpy as np
import json
import os

print("Pose Data Creator: Press a key to save the current hand pose.")
print("Pose ideas: FIST, OPEN, V, OK")
print("Press 'q' to quit.")

# MediaPipe 핸드 설정
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)
mp_drawing = mp.solutions.drawing_utils

# 웹캠 설정
cap = cv2.VideoCapture(0)

poses = {}
POSE_FILE = "poses.json"

# 기존 파일 로드
if os.path.exists(POSE_FILE):
    with open(POSE_FILE, 'r') as f:
        poses = json.load(f)
    print(f"Loaded existing poses: {list(poses.keys())}")


def normalize_landmarks(landmarks):
    """랜드마크를 손목(0번) 기준으로 정규화하고, 크기를 일정하게 만듭니다."""
    # 손목을 원점으로 이동
    wrist = np.array([landmarks[0].x, landmarks[0].y, landmarks[0].z])
    coords = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])
    coords -= wrist

    # 손의 크기를 정규화 (손목과 중지 끝 사이의 거리를 1로 만듦)
    wrist_to_mcp_middle = np.linalg.norm(coords[9])
    if wrist_to_mcp_middle == 0:
        return None
    coords /= wrist_to_mcp_middle

    return coords.flatten().tolist()


while cap.isOpened():
    success, image = cap.read()
    if not success:
        continue

    image = cv2.flip(image, 1)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = hands.process(image_rgb)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_drawing.draw_landmarks(
                image, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            key = cv2.waitKey(5) & 0xFF

            if key != 255 and key != ord('q'):
                pose_name = input("Enter pose name for the current hand shape: ").upper()
                if pose_name:
                    normalized = normalize_landmarks(hand_landmarks.landmark)
                    if normalized:
                        poses[pose_name] = normalized
                        with open(POSE_FILE, 'w') as f:
                            json.dump(poses, f, indent=4)
                        print(f"Saved pose '{pose_name}'!")
                    else:
                        print("Could not normalize landmarks. Try again.")

            elif key == ord('q'):
                break
    else:
        key = cv2.waitKey(5) & 0xFF
        if key == ord('q'):
            break

    cv2.imshow('Pose Creator', image)

cap.release()
cv2.destroyAllWindows()
hands.close()