import { PermissionsAndroid, Platform } from 'react-native';

export async function requestCamera(): Promise<boolean> {
  const r = await PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.CAMERA, {
    title: 'Camera access',
    message: 'AirCursor watches your hand with the camera. Video never leaves your phone.',
    buttonPositive: 'Allow',
  });
  return r === PermissionsAndroid.RESULTS.GRANTED;
}

export async function requestNotifications(): Promise<boolean> {
  if (Platform.OS !== 'android' || Platform.Version < 33) { return true; }
  const r = await PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.POST_NOTIFICATIONS);
  return r === PermissionsAndroid.RESULTS.GRANTED;
}
