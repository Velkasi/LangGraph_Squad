import React from 'react';
import { View, Dimensions, Platform } from 'react-native';
import { Video, ResizeMode } from 'expo-av';
import { WebView } from 'react-native-webview';
import { Video as VideoType } from '../types/db';

interface VideoPlayerProps {
  video: VideoType;
  onPlaybackStatusUpdate?: (status: any) => void;
}

const VideoPlayer: React.FC<VideoPlayerProps> = ({
  video,
  onPlaybackStatusUpdate,
}) => {
  const { width } = Dimensions.get('window');
  const height = (width * 9) / 16; // 16:9 aspect ratio

  if (!video.source_type || !video.source_ref) {
    return (
      <View style={[{ width, height }, styles.container]}>
        <Text style={styles.error}>Vidéo non disponible</Text>
      </View>
    );
  }

  const renderVideoContent = () => {
    switch (video.source_type) {
      case 'supabase': {
        const source = { uri: video.source_ref };
        return (
          <Video
            source={source}
            style={{ width, height }}
            useNativeControls
            resizeMode={ResizeMode.CONTAIN}
            onPlaybackStatusUpdate={onPlaybackStatusUpdate}
          />
        );
      }
      case 'youtube': {
        const videoId = video.source_ref;
        const youtubeUrl = `https://www.youtube.com/embed/${videoId}?enablejsapi=1`;
        return (
          <WebView
            source={{ uri: youtubeUrl }}
            style={{ width, height }}
            javaScriptEnabled={true}
            domStorageEnabled={true}
            useWebKit={true}
            scrollEnabled={false}
          />
        );
      }
      case 'vimeo': {
        const videoId = video.source_ref;
        const vimeoUrl = `https://player.vimeo.com/video/${videoId}`;
        return (
          <WebView
            source={{ uri: vimeoUrl }}
            style={{ width, height }}
            javaScriptEnabled={true}
            domStorageEnabled={true}
            useWebKit={true}
            scrollEnabled={false}
          />
        );
      }
      default:
        return (
          <View style={[{ width, height }, styles.container]}>
            <Text style={styles.error}>Type de source non supporté</Text>
          </View>
        );
    }
  };

  return <View style={styles.container}>{renderVideoContent()}</View>;
};

const styles = { container: { justifyContent: 'center', alignItems: 'center' }, error: { color: 'red', fontSize: 16 } };

export default VideoPlayer;