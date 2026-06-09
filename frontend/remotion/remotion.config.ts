// Remotion render configuration (local/offline authoring only).
import { Config } from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
Config.setConcurrency(2);
// 1080p H.264 by default; WebM via the render:tours-webm script (--codec=vp8).
Config.setCodec('h264');
