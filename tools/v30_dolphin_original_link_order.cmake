# Build-only GNU ld link group for pinned original Dolphin Libretro source.
#
# The original OpenGL GLContextLR.cpp links from dolphin_libretro_videocontexts.a
# to Common::DynamicLibrary, but libcommon.a is visited before that archive.
# A trailing "common" edge was insufficient in the real >100-library graph
# (CMake link order still emitted common before videocontexts). GNU ld must
# RESCAN all static archives before treating their unresolved symbols as
# failures. --start-group/--end-group explicitly fixes this without editing
# upstream source, using only original compiled source and corresponding
# build options. Do not confuse this with public distribution approval.
function(_anything_plays_original_dolphin_link_group)
  if(NOT TARGET dolphin_libretro OR NOT TARGET dolphin_libretro_videocontexts
      OR NOT TARGET common)
    message(FATAL_ERROR "Original Libretro Dolphin linkage targets are absent")
  endif()
  if(NOT CMAKE_SYSTEM_NAME STREQUAL "Linux")
    message(FATAL_ERROR "GNU ELF source link group is Linux-only")
  endif()
  target_link_options(dolphin_libretro PRIVATE "LINKER:--start-group")
  target_link_libraries(dolphin_libretro PRIVATE "-Wl,--end-group")
  message(STATUS "Original Dolphin source preserved: GNU linker rescan group enabled")
endfunction()
cmake_language(DEFER CALL _anything_plays_original_dolphin_link_group)
