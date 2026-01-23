#!/usr/bin/env python3
"""
Audio Player Node - Text-to-Speech service for patrol announcements
Uses gTTS for Chinese speech synthesis
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import os
import tempfile

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False


class AudioPlayerNode(Node):
    """
    A node that provides text-to-speech functionality.
    Subscribes to a topic and speaks the received text.
    """

    def __init__(self):
        super().__init__('audio_player_node')

        # Check dependencies
        if not GTTS_AVAILABLE:
            self.get_logger().warn('gTTS not available. Install with: pip3 install gTTS')
        if not PYGAME_AVAILABLE:
            self.get_logger().warn('pygame not available. Install with: pip3 install pygame')

        # Initialize pygame mixer for audio playback
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.init()
                self.get_logger().info('Audio player initialized successfully')
            except Exception as e:
                self.get_logger().error(f'Failed to initialize pygame mixer: {e}')

        # Subscriber for text to speak
        self.text_sub = self.create_subscription(
            String, '/speak', self.speak_callback, 10)

        self.get_logger().info('Audio Player Node started. Subscribe to /speak topic.')

    def speak_callback(self, msg):
        """Callback to speak the received text"""
        text = msg.data
        if not text:
            return

        self.get_logger().info(f'Speaking: {text}')
        self.speak_text(text)

    def speak_text(self, text: str, lang='zh-cn'):
        """Convert text to speech and play it"""
        if not GTTS_AVAILABLE or not PYGAME_AVAILABLE:
            self.get_logger().warn(f'TTS not available, would say: {text}')
            return False

        try:
            # Create temporary file for audio
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as fp:
                temp_file = fp.name

            # Generate speech
            tts = gTTS(text=text, lang=lang)
            tts.save(temp_file)

            # Play audio
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()

            # Wait for playback to finish
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)

            # Clean up
            os.unlink(temp_file)
            return True

        except Exception as e:
            self.get_logger().error(f'Failed to speak text: {e}')
            return False


def main(args=None):
    rclpy.init(args=args)
    node = AudioPlayerNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down...')
    finally:
        if PYGAME_AVAILABLE:
            pygame.mixer.quit()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
