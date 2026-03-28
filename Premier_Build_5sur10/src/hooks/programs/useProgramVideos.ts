import { useQuery } from '@tanstack/react-query';
import { supabase } from '../../lib/supabase';
import { Video, ProgramVideo } from '../../types/db';

interface ExtendedVideo extends Video {
  program_video: ProgramVideo;
}

export const useProgramVideos = (programId: string | null) => {
  return useQuery<ExtendedVideo[], Error>({
    queryKey: ['program_videos', programId],
    queryFn: async (): Promise<ExtendedVideo[]> => {
      if (!programId) {
        throw new Error('programId is required');
      }

      const { data, error } = await supabase
        .from('videos')
        .select(`
          *,
          program_videos!inner(
            id,
            program_id,
            video_id,
            order_index,
            created_at
          )
        `)
        .eq('program_videos.program_id', programId)
        .order('program_videos.order_index');

      if (error) {
        throw error;
      }

      return (data as ExtendedVideo[]).sort(
        (a, b) => a.program_video.order_index - b.program_video.order_index
      );
    },
    enabled: !!programId,
  });
};