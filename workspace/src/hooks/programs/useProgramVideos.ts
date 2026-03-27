import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/lib/supabase';

export const useProgramVideos = (programId: string) => {
  return useQuery({
    queryKey: ['program-videos', programId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('program_videos')
        .select(`
          id,
          order_index,
          videos:video_id (
            id,
            title,
            duration_seconds,
            source_type,
            source_ref
          )
        `)
        .eq('program_id', programId)
        .order('order_index');
      
      if (error) throw error;
      return data;
    },
    enabled: !!programId,
  });
};