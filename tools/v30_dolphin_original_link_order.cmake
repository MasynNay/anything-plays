# Original pinned libretro/dolphin at 32c61f9 has one GNU static-link order
# defect: Libretro VideoContexts/GLContextLR.cpp references
# Common::DynamicLibrary, but libcommon.a is ordered BEFORE libdolphin_libretro_videocontexts.a.
# Use CMAKE_PROJECT_TOP_LEVEL_INCLUDES to inject this BUILD-ONLY dependency
# after upstream targets are created. No upstream source file is changed.
# This file is a corresponding-source build input, not a GPL/license approval.
function(_anything_plays_original_dolphin_relink_common)
  if(NOT TARGET dolphin_libretro OR NOT TARGET dolphin_libretro_videocontexts
      OR NOT TARGET common)
    message(FATAL_ERROR "Exact original Dolphin Libretro/static common targets are absent")
  endif()
  # The late explicit edge means Common::DynamicLibrary can resolve after
  # GLContextLR.cpp is pulled out of the VideoContexts static archive on GNU ld.
  target_link_libraries(dolphin_libretro PRIVATE common)
  message(STATUS "Original Dolphin source preserved: Libretro static common relink added")
endfunction()
cmake_language(DEFER CALL _anything_plays_original_dolphin_relink_common)
