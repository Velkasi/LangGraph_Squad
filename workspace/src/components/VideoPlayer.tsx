import React from 'react';
import { View, Text, Platform } from 'react-native';
import { Video, ResizeMode } from 'expo-av';
import { WebView } from 'react-native-webview';

interface VideoPlayerProps {
  sourceType: 'supabase' | 'youtube' | 'vimeo';
  sourceRef: string;
  onPlaybackStatusUpdate?: (status: any) => void;
}

export default function VideoPlayer({
  sourceType,
  sourceRef,
  onPlaybackStatusUpdate,
}: VideoPlayerProps) {
  // Handle Web and Mobile platforms differently
  if (Platform.OS === 'web') {
    let videoUrl = '';

    switch (sourceType) {
      case 'youtube':
        videoUrl = `https://www.youtube.com/embed/${sourceRef}`;
        return (
          <WebView
            source={{ uri: videoUrl }}
            style={{ width: '100%', height: 200 }}
            javaScriptEnabled={true}
            domStorageEnabled={true}
            allowsInlineMediaPlayback={true}
          />
        );
      case 'vimeo':
        videoUrl = `https://player.vimeo.com/video/${sourceRef}`;
        return (
          <WebView
            source={{ uri: videoUrl }}
            style={{ width: '100%', height: 200 }}
            javaScriptEnabled={true}
            domStorageEnabled={true}
            allowsInlineMediaPlayback={true}
          />
        );
      case 'supabase':
        // For Supabase, we would generate a signed URL
        // This is a placeholder - actual implementation would use supabase.storage
        const signedUrl = `https://supabase-project-id.supabase.co/storage/v1/object/public/videos/${sourceRef}`;
        return (
          <video
            src={signedUrl}
            controls
            style={{ width: '100%', height: 200 }}
          />
        );
      default:
        return <Text>Unsupported video source</Text>;
    }
  } else {
    // Native mobile platforms
    let videoUri = '';

    switch (sourceType) {
      case 'supabase':
        // On mobile, we need to generate a signed URL for Supabase storage
        // This is a placeholder - actual implementation would use async fetch of signed URL
        videoUri = `https://supabase-project-id.supabase.co/storage/v1/object/public/videos/${sourceRef}`;
        return (
          <Video
            source={{ uri: videoUri }}
            style={{ width: '100%', height: 200 }}
            useNativeControls
            resizeMode={ResizeMode.CONTAIN}
            onPlaybackStatusUpdate={onPlaybackStatusUpdate}
          />
        );
      default:
        return <Text>Video playback not supported for {sourceType} on mobile</Text>;
    }
  }
}