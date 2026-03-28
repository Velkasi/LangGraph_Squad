import { useQuery } from '@tanstack/react-query';
import { supabase } from '../lib/supabase';

export interface VideoProgress {
  id: string;
  patient_id: string;
  video_id: string;
  last_position_seconds: number;
  completed: boolean;
  watched_at: string;
}

export const useVideoProgress = (patientId: string, videoId: string) => {
  return useQuery<VideoProgress | null, Error>({
    queryKey: ['videoProgress', patientId, videoId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('video_progress')
        .select('*')
        .eq('patient_id', patientId)
        .eq('video_id', videoId)
        .single();
      
      if (error) {
        if (error.code === 'PGRST116') return null; // No record found
        throw error;
      }
      
      return data;
    },
    enabled: !!patientId && !!videoId,
  });
};