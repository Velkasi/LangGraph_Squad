import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';

interface ProgramCardProps {
  title: string;
  description?: string;
  pathologyName?: string;
  videoCount: number;
  completedCount?: number;
  onPress: () => void;
}

export default function ProgramCard({
  title,
  description,
  pathologyName,
  videoCount,
  completedCount = 0,
  onPress,
}: ProgramCardProps) {
  const progress = videoCount > 0 ? (completedCount / videoCount) * 100 : 0;

  return (
    <TouchableOpacity style={styles.container} onPress={onPress}>
      <View style={styles.header}>
        <Text style={styles.title} numberOfLines={1}>
          {title}
        </Text>
        {pathologyName && (
          <Text style={styles.pathology} numberOfLines={1}>
            {pathologyName}
          </Text>
        )}
      </View>
      
      <Text style={styles.description} numberOfLines={2}>
        {description || 'Aucune description disponible'}
      </Text>
      
      <View style={styles.footer}>
        <Text style={styles.videoCount}>
          {completedCount}/{videoCount} vidéos
        </Text>
        <View style={styles.progressBarContainer}>
          <View style={[styles.progressBar, { width: `${progress}%` }]} />
        </View>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 3.84,
    elevation: 5,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    flex: 1,
  },
  pathology: {
    fontSize: 14,
    color: '#666',
    marginLeft: 8,
  },
  description: {
    fontSize: 14,
    color: '#666',
    marginBottom: 12,
    lineHeight: 20,
  },
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  videoCount: {
    fontSize: 14,
    color: '#666',
  },
  progressBarContainer: {
    flex: 1,
    height: 6,
    backgroundColor: '#e0e0e0',
    borderRadius: 3,
    marginLeft: 8,
  },
  progressBar: {
    height: '100%',
    backgroundColor: '#4CAF50',
    borderRadius: 3,
  },
});