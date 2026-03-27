import { useQuery } from '@tanstack/react-query';
import { supabase } from '../lib/supabase';

export interface ProgramVideo {
  id: string;
  program_id: string;
  video_id: string;
  order_index: number;
  video: {
    id: string;
    title: string;
    duration_seconds: number;
    source_type: 'supabase' | 'youtube' | 'vimeo';
    source_ref: string;
  };
}

export const useProgramVideos = (programId: string) => {
  return useQuery<ProgramVideo[], Error>({
    queryKey: ['programVideos', programId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('program_videos')
        .select(`
          id,
          program_id,
          video_id,
          order_index,
          video:videos(id, title, duration_seconds, source_type, source_ref)
        `)
        .eq('program_id', programId)
        .order('order_index');
      
      if (error) throw error;
      
      return data;
    },
    enabled: !!programId,
  });
};