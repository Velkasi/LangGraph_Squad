import React from 'react';
import { View, Text, Image, TouchableOpacity, StyleSheet } from 'react-native';

interface PatientCardProps {
  firstName: string;
  lastName: string;
  age?: number;
  pathology?: string;
  lastSession?: string;
  programProgress?: number;
  onPress: () => void;
}

export default function PatientCard({
  firstName,
  lastName,
  age,
  pathology,
  lastSession,
  programProgress = 0,
  onPress,
}: PatientCardProps) {
  const fullName = `${firstName} ${lastName}`;

  return (
    <TouchableOpacity style={styles.container} onPress={onPress}>
      <View style={styles.avatarContainer}>
        <Image
          source={{ uri: `https://ui-avatars.com/api/?name=${firstName}+${lastName}&background=random` }}
          style={styles.avatar}
          accessibilityLabel={`${firstName} ${lastName}`}
        />
      </View>
      
      <View style={styles.infoContainer}>
        <Text style={styles.name} numberOfLines={1}>
          {fullName}
        </Text>
        
        {pathology && (
          <Text style={styles.pathology} numberOfLines={1}>
            {pathology}
          </Text>
        )}
        
        <View style={styles.detailsRow}>
          {age && <Text style={styles.detail}>{age} ans</Text>}
          {lastSession && <Text style={styles.detail}>Dernière séance: {lastSession}</Text>}
        </View>
        
        <View style={styles.progressBarContainer}>
          <Text style={styles.progressLabel}>Progression</Text>
          <View style={styles.progressBarOuter}>
            <View style={[styles.progressBarInner, { width: `${programProgress}%` }]} />
          </View>
          <Text style={styles.progressPercent}>{programProgress}%</Text>
        </View>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 3.84,
    elevation: 5,
  },
  avatarContainer: {
    marginRight: 16,
  },
  avatar: {
    width: 50,
    height: 50,
    borderRadius: 25,
  },
  infoContainer: {
    flex: 1,
  },
  name: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 4,
  },
  pathology: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  detailsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: 8,
  },
  detail: {
    fontSize: 12,
    color: '#888',
    marginRight: 12,
  },
  progressBarContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  progressLabel: {
    fontSize: 12,
    color: '#666',
    marginRight: 8,
  },
  progressBarOuter: {
    flex: 1,
    height: 6,
    backgroundColor: '#e0e0e0',
    borderRadius: 3,
    marginRight: 8,
  },
  progressBarInner: {
    height: '100%',
    backgroundColor: '#4CAF50',
    borderRadius: 3,
  },
  progressPercent: {
    fontSize: 12,
    color: '#666',
    minWidth: 30,
  },
});