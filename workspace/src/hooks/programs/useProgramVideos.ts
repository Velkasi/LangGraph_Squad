import { useQuery } from '@tanstack/react-query';
import { supabase } from '../../lib/supabase';

export const useProgramVideos = (programId: string) => {
  return useQuery({
    queryKey: ['programVideos', programId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('program_videos')
        .select(`
          order_index,
          videos (id, title, duration_seconds, source_type, source_ref)
        `)
        .eq('program_id', programId)
        .order('order_index');
      
      if (error) {
        throw error;
      }
      
      return data?.map(item => ({
        ...item.videos,
        order_index: item.order_index
      })) || [];
    },
    enabled: !!programId,
  });
};