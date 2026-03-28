import { useQuery } from '@tanstack/react-query';
import { supabase } from '../../lib/supabase';

export const useVideoProgress = (patientId: string, videoId: string) => {
  return useQuery({
    queryKey: ['videoProgress', patientId, videoId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('video_progress')
        .select('last_position_seconds, completed, watched_at')
        .eq('patient_id', patientId)
        .eq('video_id', videoId)
        .maybeSingle();
      
      if (error) {
        throw error;
      }
      
      return data;
    },
    enabled: !!patientId && !!videoId,
  });
};