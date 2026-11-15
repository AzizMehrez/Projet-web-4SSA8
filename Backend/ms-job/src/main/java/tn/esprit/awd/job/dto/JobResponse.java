package tn.esprit.awd.job.dto;

import java.time.LocalDate;

public record JobResponse(
        Long id,
        String name,
        String description,
        boolean available,
        LocalDate date,
        CategoryResponse category
) {
}
