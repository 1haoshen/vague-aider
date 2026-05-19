"""Main PhoneAgent class for orchestrating phone automation."""

import json
import os
import time
import traceback
import base64
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Callable

from phone_agent.actions import ActionHandler
from phone_agent.actions.handler import do, finish, parse_action
from phone_agent.config import get_messages, get_system_prompt
from phone_agent.device_factory import get_device_factory
from phone_agent.model import ModelClient, ModelConfig
from phone_agent.model.client import MessageBuilder
from PIL import Image


@dataclass
class AgentConfig:
    """Configuration for the PhoneAgent."""

    max_steps: int = 300
    device_id: str | None = None
    lang: str = "cn"
    system_prompt: str | None = None
    verbose: bool = True
    log_dir: str | None = None  # Log directory path, None to disable logging
    run_name: str = "test"  # Run name for log organization

    def __post_init__(self):
        if self.system_prompt is None:
            self.system_prompt = get_system_prompt(self.lang)


@dataclass
class StepResult:
    """Result of a single agent step."""

    success: bool
    finished: bool
    action: dict[str, Any] | None
    thinking: str
    message: str | None = None


class PhoneAgent:
    """
    AI-powered agent for automating Android phone interactions.

    The agent uses a vision-language model to understand screen content
    and decide on actions to complete user tasks.

    Args:
        model_config: Configuration for the AI model.
        agent_config: Configuration for the agent behavior.
        confirmation_callback: Optional callback for sensitive action confirmation.
        takeover_callback: Optional callback for takeover requests.

    Example:
        >>> from phone_agent import PhoneAgent
        >>> from phone_agent.model import ModelConfig
        >>>
        >>> model_config = ModelConfig(base_url="http://localhost:8000/v1")
        >>> agent = PhoneAgent(model_config)
        >>> agent.run("Open WeChat and send a message to John")
    """

    def __init__(
        self,
        model_config: ModelConfig | None = None,
        agent_config: AgentConfig | None = None,
        confirmation_callback: Callable[[str], bool] | None = None,
        takeover_callback: Callable[[str], None] | None = None,
    ):
        self.model_config = model_config or ModelConfig()
        self.agent_config = agent_config or AgentConfig()

        self.model_client = ModelClient(self.model_config)
        self.action_handler = ActionHandler(
            device_id=self.agent_config.device_id,
            confirmation_callback=confirmation_callback,
            takeover_callback=takeover_callback,
        )

        self._context: list[dict[str, Any]] = []
        self._step_count = 0
        self._log_dir: str | None = None
        self._steps_log: list[dict[str, Any]] = []
        self._task_start_time: float | None = None

    def run(self, task: str) -> str:
        """
        Run the agent to complete a task.

        Args:
            task: Natural language description of the task.

        Returns:
            Final message from the agent.
        """
        self._context = []
        self._step_count = 0
        self._steps_log = []
        self._task_start_time = time.time()
        
        # Initialize logging if enabled
        if self.agent_config.log_dir:
            task_id = time.strftime("%Y%m%d-%H%M%S")
            self._log_dir = f"{self.agent_config.log_dir}/{self.agent_config.run_name}/{task_id}"
            os.makedirs(f"{self._log_dir}/screenshots", exist_ok=True)
            
            # Initialize steps.json with task info
            self._steps_log.append({
                "step": 0,
                "operation": "init",
                "instruction": task,
                "task_id": task_id,
                "run_name": self.agent_config.run_name,
                "max_steps": self.agent_config.max_steps,
            })
            self._save_steps_log()

        # First step with user prompt
        result = self._execute_step(task, is_first=True)

        if result.finished:
            return result.message or "Task completed"

        # Continue until finished or max steps reached
        while self._step_count < self.agent_config.max_steps:
            result = self._execute_step(is_first=False)

            if result.finished:
                if self._log_dir:
                    task_end_time = time.time()
                    self._steps_log.append({
                        "step": self._step_count,
                        "operation": "finish",
                        "finish_flag": "success",
                        "task_duration": task_end_time - self._task_start_time,
                    })
                    self._save_steps_log()
                return result.message or "Task completed"

        if self._log_dir:
            task_end_time = time.time()
            self._steps_log.append({
                "step": self._step_count,
                "operation": "finish",
                "finish_flag": "max_steps_reached",
                "task_duration": task_end_time - self._task_start_time,
            })
            self._save_steps_log()
        return "Max steps reached"

    def step(self, task: str | None = None) -> StepResult:
        """
        Execute a single step of the agent.

        Useful for manual control or debugging.

        Args:
            task: Task description (only needed for first step).

        Returns:
            StepResult with step details.
        """
        is_first = len(self._context) == 0

        if is_first and not task:
            raise ValueError("Task is required for the first step")

        return self._execute_step(task, is_first)

    def reset(self) -> None:
        """Reset the agent state for a new task."""
        self._context = []
        self._step_count = 0

    def _execute_step(
        self, user_prompt: str | None = None, is_first: bool = False
    ) -> StepResult:
        """Execute a single step of the agent loop."""
        self._step_count += 1
        step_start_time = time.time()

        # Capture current screen state
        device_factory = get_device_factory()
        screenshot = device_factory.get_screenshot(self.agent_config.device_id)
        current_app = device_factory.get_current_app(self.agent_config.device_id)

        # Save screenshot if logging is enabled
        screenshot_path = None
        if self._log_dir:
            screenshot_path = f"{self._log_dir}/screenshots/{self._step_count}.jpg"
            try:
                # Decode base64 image and save as JPG
                image_data = base64.b64decode(screenshot.base64_data)
                image = Image.open(BytesIO(image_data))
                # Convert to RGB if necessary (for PNG with transparency)
                if image.mode in ('RGBA', 'LA', 'P'):
                    rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                    if image.mode == 'P':
                        image = image.convert('RGBA')
                    rgb_image.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
                    image = rgb_image
                image.save(screenshot_path, "JPEG", quality=95)
            except Exception as e:
                if self.agent_config.verbose:
                    print(f"Warning: Failed to save screenshot: {e}")

        # Build messages
        if is_first:
            self._context.append(
                MessageBuilder.create_system_message(self.agent_config.system_prompt)
            )

            screen_info = MessageBuilder.build_screen_info(current_app)
            text_content = f"{user_prompt}\n\n{screen_info}"

            self._context.append(
                MessageBuilder.create_user_message(
                    text=text_content, image_base64=screenshot.base64_data
                )
            )
            prompt_action = text_content  # For logging
        else:
            screen_info = MessageBuilder.build_screen_info(current_app)
            text_content = f"** Screen Info **\n\n{screen_info}"

            self._context.append(
                MessageBuilder.create_user_message(
                    text=text_content, image_base64=screenshot.base64_data
                )
            )
            prompt_action = text_content  # For logging

        # Get model response
        try:
            msgs = get_messages(self.agent_config.lang)
            print("\n" + "=" * 50)
            print(f"💭 {msgs['thinking']}:")
            print("-" * 50)
            response = self.model_client.request(self._context)
        except Exception as e:
            if self.agent_config.verbose:
                traceback.print_exc()
            return StepResult(
                success=False,
                finished=True,
                action=None,
                thinking="",
                message=f"Model error: {e}",
            )

        # Parse action from response
        try:
            action = parse_action(response.action)
        except ValueError:
            if self.agent_config.verbose:
                traceback.print_exc()
            action = finish(message=response.action)

        if self.agent_config.verbose:
            # Print thinking process
            print("-" * 50)
            print(f"🎯 {msgs['action']}:")
            print(json.dumps(action, ensure_ascii=False, indent=2))
            print("=" * 50 + "\n")

        # Remove image from context to save space
        self._context[-1] = MessageBuilder.remove_images_from_message(self._context[-1])

        # Execute action
        action_start_time = time.time()
        try:
            result = self.action_handler.execute(
                action, screenshot.width, screenshot.height
            )
        except Exception as e:
            if self.agent_config.verbose:
                traceback.print_exc()
            result = self.action_handler.execute(
                finish(message=str(e)), screenshot.width, screenshot.height
            )
        action_end_time = time.time()

        # Add assistant response to context
        self._context.append(
            MessageBuilder.create_assistant_message(
                f"<think>{response.thinking}</think><answer>{response.action}</answer>"
            )
        )

        # Log step information
        if self._log_dir:
            step_end_time = time.time()
            step_log = {
                "step": self._step_count,
                "operation": "action",
                "screenshot": screenshot_path,
                "prompt_action": prompt_action,
                "raw_response": response.raw_content,
                "action_object": action,
                "action_thought": response.thinking,
                "duration": step_end_time - step_start_time,
                "action_execution_duration": action_end_time - action_start_time,
            }
            
            # Add token usage information (similar to Mobile-Agent-E format)
            # Note: 
            # - prompt_tokens: 输入 token（包括 system prompt + prompt_action + 历史上下文）
            # - completion_tokens: 输出 token（包括 action_thought + action）
            # - action_thought 是输出，属于 completion_tokens，不是 prompt_tokens
            if response.prompt_tokens is not None:
                step_log["prompt_tokens"] = response.prompt_tokens
                # prompt_action_tokens 表示 action 阶段的 prompt token 使用
                # 在 phone-agent 中，由于没有独立的规划阶段，prompt_tokens 就是 prompt_action_tokens
                step_log["prompt_action_tokens"] = response.prompt_tokens
            if response.completion_tokens is not None:
                step_log["completion_tokens"] = response.completion_tokens
                # completion_tokens 包括 action_thought（思考）和 action（动作）两部分
                # 如果需要区分，可以估算，但 action_thought 属于输出，不是输入
            if response.total_tokens is not None:
                step_log["total_tokens"] = response.total_tokens
            
            self._steps_log.append(step_log)
            self._save_steps_log()

        # Check if finished
        finished = action.get("_metadata") == "finish" or result.should_finish

        if finished and self.agent_config.verbose:
            msgs = get_messages(self.agent_config.lang)
            print("\n" + "🎉 " + "=" * 48)
            print(
                f"✅ {msgs['task_completed']}: {result.message or action.get('message', msgs['done'])}"
            )
            print("=" * 50 + "\n")

        return StepResult(
            success=result.success,
            finished=finished,
            action=action,
            thinking=response.thinking,
            message=result.message or action.get("message"),
        )

    @property
    def context(self) -> list[dict[str, Any]]:
        """Get the current conversation context."""
        return self._context.copy()

    @property
    def step_count(self) -> int:
        """Get the current step count."""
        return self._step_count

    def _save_steps_log(self) -> None:
        """Save steps log to JSON file."""
        if not self._log_dir:
            return
        log_json_path = f"{self._log_dir}/steps.json"
        try:
            with open(log_json_path, "w", encoding="utf-8") as f:
                json.dump(self._steps_log, f, indent=4, ensure_ascii=False)
        except Exception as e:
            if self.agent_config.verbose:
                print(f"Warning: Failed to save steps log: {e}")
