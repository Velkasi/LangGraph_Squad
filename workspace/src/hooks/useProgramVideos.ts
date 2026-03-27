import { useState, useEffect } from 'react';
import { supabase } from '../lib/supabase';

interface Video {
  id: string;
  title: string;
  duration_seconds: number;
  source_type: 'supabase' | 'youtube' | 'vimeo';
  source_ref: string;
  created_at: string;
}

interface ProgramVideo {
  id: string;
  program_id: string;
  video_id: string;
  order_index: number;
  video: Video;
}

export function useProgramVideos(programId: string | undefined) {
  const [videos, setVideos] = useState<ProgramVideo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function getVideos() {
      if (!programId) {
        setVideos([]);
        setLoading(false);
        return;
      }

      try {
        const { data, error } = await supabase
          .from('program_videos')
          .select(`
            id,
            program_id,
            video_id,
            order_index,
            video:videos!inner(
              id,
              title,
              duration_seconds,
              source_type,
              source_ref,
              created_at
            )
          `)
          .eq('program_id', programId)
          .order('order_index', { ascending: true });

        if (error) throw error;

        setVideos(data);
      } catch (error) {
        console.error('Error fetching program videos:', error);
        setVideos([]);
      } finally {
        setLoading(false);
      }
    }

    getVideos();
  }, [programId]);

  return { videos, loading };
}