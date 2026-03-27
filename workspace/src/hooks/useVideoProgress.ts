import { useState, useEffect } from 'react';
import { useCurrentUser } from './useCurrentUser';
import { supabase } from '../lib/supabase';

interface VideoProgress {
  id: string;
  patient_id: string;
  video_id: string;
  last_position_seconds: number;
  completed: boolean;
  watched_at: string;
}

export function useVideoProgress(videoId: string | undefined) {
  const { user, loading: userLoading } = useCurrentUser();
  const [progress, setProgress] = useState<VideoProgress | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function getProgress() {
      if (!user || !videoId || user.role !== 'patient') {
        setProgress(null);
        setLoading(false);
        return;
      }

      try {
        const { data, error } = await supabase
          .from('video_progress')
          .select('*')
          .eq('patient_id', user.id)
          .eq('video_id', videoId)
          .single();

        if (error && error.code !== 'PGRST116') throw error; // PGRST116 = no rows found

        setProgress(data || null);
      } catch (error) {
        console.error('Error fetching video progress:', error);
        setProgress(null);
      } finally {
        setLoading(false);
      }
    }

    getProgress();
  }, [user, videoId]);

  return { progress, loading: loading || userLoading };
}