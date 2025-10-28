import numpy as np
import json

class PoseComparator:
    """저장된 포즈와 실시간 랜드마크를 비교하여 현재 포즈를 인식하는 클래스"""
    def __init__(self, pose_file='poses.json', threshold=0.85):
        self.pose_library = self._load_poses(pose_file)
        self.similarity_threshold = threshold
        print(f"Pose library loaded with: {list(self.pose_library.keys())}")

    def _load_poses(self, pose_file):
        try:
            with open(pose_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: {pose_file} not found. Please run create_pose_data.py first.")
            return {}

    def _normalize_landmarks(self, landmarks):
        """실시간 랜드마크를 정규화합니다."""
        if not landmarks:
            return None
        
        coords = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])
        wrist = coords[0]
        coords -= wrist

        wrist_to_mcp_middle = np.linalg.norm(coords[9])
        if wrist_to_mcp_middle == 0:
            return None
        coords /= wrist_to_mcp_middle
        
        return coords.flatten()

    def match_pose(self, live_landmarks):
        """실시간 랜드마크와 라이브러리의 모든 포즈를 비교하여 가장 유사한 포즈를 찾습니다."""
        if not live_landmarks or not self.pose_library:
            return "UNKNOWN", 0.0

        normalized_live = self._normalize_landmarks(live_landmarks)
        if normalized_live is None:
            return "UNKNOWN", 0.0

        best_match_pose = "UNKNOWN"
        max_similarity = 0.0

        for pose_name, pose_landmarks in self.pose_library.items():
            pose_vec = np.array(pose_landmarks)
            
            # 코사인 유사도 계산
            similarity = np.dot(normalized_live, pose_vec) / (np.linalg.norm(normalized_live) * np.linalg.norm(pose_vec))

            if similarity > max_similarity:
                max_similarity = similarity
                best_match_pose = pose_name

        if max_similarity < self.similarity_threshold:
            return "UNKNOWN", max_similarity

        return best_match_pose, max_similarity