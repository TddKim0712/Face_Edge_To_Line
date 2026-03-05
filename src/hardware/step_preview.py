## for debugging
## step 수를 미리 볼 수 있게끔 사용
## step_preview.py

import kinematics


def gcode_to_steps(paths):

    step_paths = []

    for p in paths:

        steps = []

        for pt in p:

            sx, sy = kinematics.mm_to_steps(pt[0], pt[1])

            steps.append((sx, sy))

        step_paths.append(steps)

    return step_paths