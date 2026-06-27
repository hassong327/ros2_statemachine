# state_machine

ROS 2에서 YAML 설정 파일만으로 토픽 기반 상태 머신을 실행하는 Python 패키지입니다.

이 노드는 설정된 입력 토픽을 구독하고, 최근 입력값을 기준으로 상태 전이 조건을 평가한 뒤,
설정된 출력 토픽으로 명령값을 발행합니다.

## 주요 기능

- YAML 파일로 상태, 전이 조건, 출력 액션 설정
- `std_msgs/msg/String`, `std_msgs/msg/Bool` 같은 ROS 2 메시지 타입 사용
- 입력 메시지의 특정 필드 읽기
- 출력 메시지의 특정 필드에 값 쓰기
- 현재 상태를 `/state_machine/current_state` 토픽으로 발행

## 설치 및 빌드

ROS 2 워크스페이스의 `src` 폴더에 저장소를 받은 뒤 빌드합니다.

```bash
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src
git clone https://github.com/hassong327/ros2_statemachine.git

cd ~/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --packages-select state_machine
source install/setup.bash
```

이미 현재 폴더에 파일이 있다면, 해당 폴더가 ROS 2 워크스페이스의 `src` 아래에 있도록 둔 뒤
워크스페이스 루트에서 `colcon build`를 실행하면 됩니다.

## 실행

기본 설정 파일로 실행:

```bash
ros2 launch state_machine state_machine.launch.py
```

다른 YAML 설정 파일로 실행:

```bash
ros2 launch state_machine state_machine.launch.py config_file:=/absolute/path/to/state_machine.yaml
```

노드만 직접 실행할 수도 있습니다.

```bash
ros2 run state_machine state_machine_node --ros-args -p config_file:=/absolute/path/to/state_machine.yaml
```

## 기본 예제 동작

기본 설정 파일은 [config/state_machine.yaml](config/state_machine.yaml)입니다.

입력 토픽:

- `/traffic_light` (`std_msgs/msg/String`)
- `/obstacle_detected` (`std_msgs/msg/Bool`)

출력 토픽:

- `/behavior_cmd` (`std_msgs/msg/String`)
- `/state_machine/current_state` (`std_msgs/msg/String`)

기본 상태 흐름:

- 시작 상태는 `IDLE`
- `IDLE` 진입 시 `/behavior_cmd`에 `STOP` 발행
- `/traffic_light`가 `GREEN`이면 `DRIVE`로 전이하고 `DRIVE` 발행
- `DRIVE` 상태에서 `/obstacle_detected`가 `true`이면 `AVOID`로 전이하고 `AVOID` 발행
- `AVOID` 상태에서 `/obstacle_detected`가 `false`이면 `DRIVE`로 복귀하고 `DRIVE` 발행
- `DRIVE` 상태에서 `/traffic_light`가 `RED`이면 `STOP`으로 전이하고 `STOP` 발행

## 테스트 방법

터미널 1에서 상태 머신을 실행합니다.

```bash
ros2 launch state_machine state_machine.launch.py
```

터미널 2에서 출력 명령을 확인합니다.

```bash
ros2 topic echo /behavior_cmd
```

터미널 3에서 현재 상태를 확인합니다.

```bash
ros2 topic echo /state_machine/current_state
```

다른 터미널에서 입력 토픽을 발행해 상태 전이를 테스트합니다.

```bash
ros2 topic pub /traffic_light std_msgs/msg/String "{data: GREEN}" --once
ros2 topic pub /obstacle_detected std_msgs/msg/Bool "{data: true}" --once
ros2 topic pub /obstacle_detected std_msgs/msg/Bool "{data: false}" --once
ros2 topic pub /traffic_light std_msgs/msg/String "{data: RED}" --once
```

예상 흐름:

```text
IDLE -> DRIVE -> AVOID -> DRIVE -> STOP
```

## YAML 설정 작성법

설정 파일의 기본 구조는 다음과 같습니다.

```yaml
state_machine:
  update_rate_hz: 10.0
  initial_state: IDLE
  status_topic: ~/current_state

  inputs:
    traffic_light:
      topic: /traffic_light
      type: std_msgs/msg/String
      field: data

  outputs:
    behavior_cmd:
      topic: /behavior_cmd
      type: std_msgs/msg/String
      field: data

  states:
    IDLE:
      on_enter:
        - output: behavior_cmd
          value: STOP
      transitions:
        - when:
            input: traffic_light
            op: "=="
            value: GREEN
          to: DRIVE
          actions:
            - output: behavior_cmd
              value: DRIVE

    DRIVE:
      transitions: []
```

### 최상위 옵션

- `update_rate_hz`: 상태 전이 조건을 평가하는 주기입니다.
- `initial_state`: 노드 시작 시 사용할 초기 상태입니다.
- `status_topic`: 현재 상태를 발행할 토픽입니다. 기본 예제의 `~/current_state`는 노드 이름 때문에 `/state_machine/current_state`로 해석됩니다.

### inputs

입력 토픽을 정의합니다.

```yaml
inputs:
  obstacle:
    topic: /obstacle_detected
    type: std_msgs/msg/Bool
    field: data
    qos_depth: 10
```

- `topic`: 구독할 토픽 이름
- `type`: ROS 2 메시지 타입
- `field`: 조건 평가에 사용할 메시지 필드
- `qos_depth`: 선택 항목이며 기본값은 `10`

`field`에는 `data`뿐 아니라 `pose.position.x`처럼 중첩 필드도 사용할 수 있습니다.

### outputs

출력 토픽을 정의합니다.

```yaml
outputs:
  behavior_cmd:
    topic: /behavior_cmd
    type: std_msgs/msg/String
    field: data
    qos_depth: 10
```

액션에서 `output: behavior_cmd`를 사용하면 이 토픽으로 메시지가 발행됩니다.

### states

상태별 진입 액션과 전이 조건을 정의합니다.

```yaml
states:
  DRIVE:
    transitions:
      - when:
          input: obstacle
          op: "=="
          value: true
        to: AVOID
        actions:
          - output: behavior_cmd
            value: AVOID
```

- `on_enter`: 해당 상태에 진입했을 때 한 번 실행할 액션 목록
- `transitions`: 현재 상태에서 평가할 전이 목록
- `when`: 전이 조건
- `to`: 조건이 참일 때 이동할 상태 이름
- `actions`: 전이 직후 실행할 출력 액션 목록

전이 조건은 위에서부터 순서대로 검사하며, 참인 조건을 찾으면 해당 전이 하나만 실행합니다.

## 조건 연산자

지원하는 `op` 값:

- `==`
- `!=`
- `>`
- `>=`
- `<`
- `<=`
- `exists`
- `not_exists`

여러 조건을 함께 사용할 수도 있습니다.

```yaml
when:
  all:
    - input: traffic_light
      op: "=="
      value: GREEN
    - input: obstacle
      op: "=="
      value: false
```

```yaml
when:
  any:
    - input: traffic_light
      op: "=="
      value: RED
    - input: obstacle
      op: "=="
      value: true
```

## 문제 해결

패키지를 찾을 수 없는 경우:

```bash
source ~/ros2_ws/install/setup.bash
ros2 pkg list | grep state_machine
```

토픽이 발행되지 않는 경우:

```bash
ros2 topic list
ros2 topic echo /state_machine/current_state
ros2 topic echo /behavior_cmd
```

설정 파일 오류가 나는 경우:

- `initial_state`가 `states` 안에 정의되어 있는지 확인합니다.
- `to`에 적은 상태 이름이 `states` 안에 있는지 확인합니다.
- `input` 이름이 `inputs` 안에 정의되어 있는지 확인합니다.
- `output` 이름이 `outputs` 안에 정의되어 있는지 확인합니다.
- 메시지 타입 패키지가 설치되어 있고 현재 터미널에 `source install/setup.bash`가 되어 있는지 확인합니다.
