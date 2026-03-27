import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/lib/supabase';

export const useVideoProgress = (patientId: string, videoId: string) => {
  return useQuery({
    queryKey: ['video-progress', patientId, videoId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('video_progress')
        .select('*')
        .eq('patient_id', patientId)
        .eq('video_id', videoId)
        .single();
      
      if (error) {
        if (error.code === 'PGRST116') return null; // No data found
        throw error;
      }
      
      return data;
    },
    enabled: !!patientId && !!videoId,
  });
};