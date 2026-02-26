## 펜 플로터 머신 vision.py
## 2026 SIOR spring 홍보부스용
## edited: 02/26/2026

### 기계가 처리 가능한 벡터아트/polygon만 남기기
## vision 내부 ->  normalize 이후에 호출하여 적용하기


import numpy as np

# =========================
# 1. Polyline total length

def polyline_length(points):
    if len(points) < 2:
        return 0.0
    return np.sum(np.linalg.norm(points[1:] - points[:-1], axis=1))


# =========================
# 2. Remove short polylines

def filter_short_paths(paths, min_length):
    out = []
    for p in paths:
        if polyline_length(p) >= min_length:
            out.append(p)
    return out


# =========================
# 3. Remove short segments

def remove_short_segments(points, min_segment):
    if len(points) < 2:
        return points

    new_pts = [points[0]]

    for i in range(1, len(points)):
        if np.linalg.norm(points[i] - new_pts[-1]) >= min_segment:
            new_pts.append(points[i])

    return np.array(new_pts)


# =========================
# 4. Angle-based simplification

def remove_small_angle(points, angle_thresh_deg):

    if len(points) < 3:
        return points

    angle_thresh = np.deg2rad(angle_thresh_deg)
    new_pts = [points[0]]

    for i in range(1, len(points)-1):

        a = new_pts[-1]
        b = points[i]
        c = points[i+1]

        v1 = b - a
        v2 = c - b

        if np.linalg.norm(v1) == 0 or np.linalg.norm(v2) == 0:
            continue

        cosang = np.dot(v1, v2) / (np.linalg.norm(v1)*np.linalg.norm(v2))
        cosang = np.clip(cosang, -1.0, 1.0)

        angle = np.arccos(cosang)

        if angle >= angle_thresh:
            new_pts.append(b)

    new_pts.append(points[-1])

    return np.array(new_pts)


# =========================
# 5. Uniform resampling

def resample_uniform(points, spacing):

    if len(points) < 2:
        return points

    dists = np.linalg.norm(points[1:] - points[:-1], axis=1)
    cumdist = np.insert(np.cumsum(dists), 0, 0)

    total_len = cumdist[-1]
    new_distances = np.arange(0, total_len, spacing)

    new_pts = []

    for d in new_distances:
        idx = np.searchsorted(cumdist, d)
        if idx >= len(points):
            break

        if idx == 0:
            new_pts.append(points[0])
        else:
            t = (d - cumdist[idx-1]) / (cumdist[idx] - cumdist[idx-1] + 1e-8)
            pt = points[idx-1] + t * (points[idx] - points[idx-1])
            new_pts.append(pt)

    return np.array(new_pts)


# =========================
# Master pipeline

def postprocess_paths(paths,
                      min_poly_length,
                      min_segment_length,
                      angle_thresh_deg,
                      resample_spacing):

    out = []

    paths = filter_short_paths(paths, min_poly_length)

    for p in paths:

        p = remove_short_segments(p, min_segment_length)
        p = remove_small_angle(p, angle_thresh_deg)
        p = resample_uniform(p, resample_spacing)

        if len(p) >= 2:
            out.append(p)

    return out