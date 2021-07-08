/**
 * @file
 * @brief Ruler directives (dragging playhead functionality, progress bars, tick marks, etc...)
 * @author Jonathan Thomas <jonathan@openshot.org>
 * @author Cody Parker <cody@yourcodepro.com>
 *
 * @section LICENSE
 *
 * Copyright (c) 2008-2018 OpenShot Studios, LLC
 * <http://www.openshotstudios.com/>. This file is part of
 * OpenShot Video Editor, an open-source project dedicated to
 * delivering high quality video editing and animation solutions to the
 * world. For more information visit <http://www.openshot.org/>.
 *
 * OpenShot Video Editor is free software: you can redistribute it
 * and/or modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * OpenShot Video Editor is distributed in the hope that it will be
 * useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with OpenShot Library.  If not, see <http://www.gnu.org/licenses/>.
 */


// Variables for panning by middle click
var is_scrolling = false;
var starting_scrollbar = {x: 0, y: 0};
var starting_mouse_position = {x: 0, y: 0};

// Variables for scrolling control
var scroll_left_pixels = 0;


// This container allows for tracks to be scrolled (with synced ruler)
// and allows for panning of the timeline with the middle mouse button
/*global App, secondsToTime*/
App.directive("tlScrollableTracks", function () {
  return {
    restrict: "A",
    link: function (scope, element, attrs) {

      // Sync ruler to track scrolling
      element.on("scroll", function () {
        //set amount scrolled
        scroll_left_pixels = element.scrollLeft();

        $("#track_controls").scrollTop(element.scrollTop());
        $("#scrolling_ruler").scrollLeft(element.scrollLeft());
        $("#progress_container").scrollLeft(element.scrollLeft());

        scope.$apply( () => {
          scope.scrollLeft = element[0].scrollLeft;
        })

        // Send scrollbar position to Qt
        if (scope.Qt) {
           // Calculate scrollbar positions (left and right edge of scrollbar)
           var timeline_length = scope.getTimelineWidth(0);
           var left_scrollbar_edge = scroll_left_pixels / timeline_length;
           var right_scrollbar_edge = (scroll_left_pixels + element.width()) / timeline_length;

           // Send normalized scrollbar positions to Qt
           timeline.ScrollbarChanged([left_scrollbar_edge, right_scrollbar_edge, timeline_length, element.width()]);
        }

        scope.$apply( () => {
          scope.scrollLeft = element[0].scrollLeft;
        })

      });

      // Initialize panning when middle mouse is clicked
      element.on("mousedown", function (e) {
        if (e.which === 2) { // middle button
          e.preventDefault();
          is_scrolling = true;
          starting_scrollbar = {x: element.scrollLeft(), y: element.scrollTop()};
          starting_mouse_position = {x: e.pageX, y: e.pageY};
          element.addClass("drag_cursor");
        }
      });

      // Pans the timeline (on middle mouse clip and drag)
      element.on("mousemove", function (e) {
        if (is_scrolling) {
          // Calculate difference from last position
          var difference = {x: starting_mouse_position.x - e.pageX, y: starting_mouse_position.y - e.pageY};

          // Scroll the tracks div
          element.scrollLeft(starting_scrollbar.x + difference.x);
          element.scrollTop(starting_scrollbar.y + difference.y);
        }
      });

      // Remove move cursor (i.e. dragging has stopped)
      element.on("mouseup", function (e) {
        element.removeClass("drag_cursor");
      });

    }
  };
});

// Track scrolling mode on body tag... allows for capture of released middle mouse button
App.directive("tlBody", function () {
  return {
    link: function (scope, element, attrs) {

      element.on("mouseup", function (e) {
        if (e.which === 2) { // middle button
          is_scrolling = false;
        }
      });

    }
  };
});


// The HTML5 canvas ruler
App.directive("tlRuler", function ($timeout) {
  return {
    restrict: "A",
    link: function (scope, element, attrs) {
      //on click of the ruler canvas, jump playhead to the clicked spot
      element.on("mousedown", function (e) {
        // Get playhead position
        var playhead_left = e.pageX - element.offset().left;
        var playhead_seconds = playhead_left / scope.pixelsPerSecond;

        // Immediately preview frame (don't wait for animated playhead)
        scope.previewFrame(playhead_seconds);

        // Animate to new position (and then update scope)
        scope.playhead_animating = true;
        $(".playhead-line").animate({left: playhead_left}, 200);
        $(".playhead-top").animate({left: playhead_left}, 200, function () {
          // Update playhead
          scope.movePlayhead(playhead_seconds);

          // Animation complete.
          scope.$apply(function () {
            scope.playhead_animating = false;
          });
        });
      });

      // Move playhead to new position (if it's not currently being animated)
      element.on("mousemove", function (e) {
        if (e.which === 1 && !scope.playhead_animating) { // left button
          var playhead_seconds = (e.pageX - element.offset().left) / scope.pixelsPerSecond;
          // Update playhead
          scope.movePlayhead(playhead_seconds);
          scope.previewFrame(playhead_seconds);
        }
      });

      drawTimes = () => {
        ruler = $("#ruler");
        width = $("body").width();
        $("#ruler span").remove();
        start = Math.max(scope.scrollLeft - width, 100);
        end = Math.min(scope.scrollLeft + (2*width), $('#ruler').width());

        scale = scope.project.scale;
        for (var i = start - (start % 100) ; i < end; i += 100) {
          /* create and format span */
          s = $('<span style="left: ' + i + 'px;">');
          s.addClass("ruler_time");

          /* Calculate Time */
          var time = i  / scope.pixelsPerSecond;
          var text_time = secondsToTime(time, scope.project.fps.num, scope.project.fps.den);
          s[0].innerText= text_time["hour"] + ":" + text_time["min"] + ":" + text_time["sec"];
          if (scope.project.scale < 1) {
            s[0].innerText += ',' + text_time['frame'];
          }

          ruler.append(s);
        }
      }

      scope.$watch("project.scale + project.duration + scrollLeft", function (val) {
        if (val) {
          $timeout(function () {
            drawTimes();
            return;
          } , 0);
        }
      });

    }

  };
});
