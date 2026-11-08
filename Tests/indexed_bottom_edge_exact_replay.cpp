#include "NativeIndexedPresentation.h"
#include <cassert>
#include <cstring>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>
std::vector<uint8_t> file(const std::string&p){std::ifstream f(p,std::ios::binary);assert(f);return {std::istreambuf_iterator<char>(f),std::istreambuf_iterator<char>()};}
int main(int argc,char**argv){assert(argc==2);std::string root=argv[1];auto before=file(root+"/initial.bin"),scratch=file(root+"/scratch.bin"),rgb=file(root+"/palette.bin"),pid=file(root+"/fixture.pid");constexpr size_t full=640*481,visible=640*480;assert(before.size()==full&&scratch.size()==129&&rgb.size()==768);std::ifstream manifest(root+"/manifest.txt");assert(manifest);unsigned id,mode,render,fx,fy;size_t writes;std::string prefix;unsigned count=0;
 while(manifest>>id>>mode>>render>>fx>>fy>>writes>>prefix){auto commandBytes=file(prefix+"-command.bin"),stateBytes=file(prefix+"-state.bin"),lut=file(prefix+"-table.bin"),expected=file(prefix+"-expected.bin"),cover=file(prefix+"-coverage.bin"),afterScratch=file(prefix+"-scratch.bin");assert(commandBytes.size()==sizeof(ClawPIDBlitCommand)&&stateBytes.size()==sizeof(ClawLightPIDBlitState));ClawPIDBlitCommand command{};ClawLightPIDBlitState state{};std::memcpy(&command,commandBytes.data(),sizeof command);std::memcpy(&state,stateBytes.data(),sizeof state);ClawLightPIDBlitTable table{{1,uint32_t(lut.size()),0x1040000},lut.data(),lut.size()};assert(state.effectMode==mode&&state.renderWord==render&&command.flipX==fx&&command.flipY==fy);
 for(size_t capacity:{full,visible}){std::vector<uint8_t> output(before.begin(),before.begin()+capacity),mask(capacity,0x41),live(scratch.begin(),scratch.end());ClawNativeIndexedImage image{};ClawLightPIDBlitInfo info{};uint32_t done=claw_native_indexed_composite8(pid.data(),pid.size(),&command,&state,&table,output.data(),mask.data(),capacity,640,live.data(),live.size(),rgb.data(),rgb.size(),640,480,&info,&image);bool rejected=capacity==visible&&(fx||(mode==2&&render==1));
 if(rejected){assert(!done&&!image.rgba&&live==scratch);assert(std::memcmp(output.data(),before.data(),capacity)==0);for(uint8_t b:mask)assert(b==0);}
 else{assert(done&&image.rgba);assert(std::memcmp(output.data(),expected.data(),capacity)==0&&std::memcmp(mask.data(),cover.data(),capacity)==0&&live==afterScratch);assert(info.writes==writes);assert(image.left==(fx?639u:638u)&&image.top==479&&image.width==(fx?1u:2u)&&image.height==1&&image.byteCount==image.width*4);for(size_t x=0;x<image.width;++x){unsigned index=output[479*640+image.left+x];assert(std::memcmp(image.rgba+x*4,rgb.data()+index*3,3)==0&&image.rgba[x*4+3]==255);}}
 claw_native_indexed_image_dispose(&image);
 }++count;}
 assert(count==25);
}
